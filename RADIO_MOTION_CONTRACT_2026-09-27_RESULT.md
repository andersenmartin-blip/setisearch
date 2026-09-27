# Motion provenance correction and conditional coverage — 27 September 2026

**A missing catalogue limit flag changes the interpretation of the working
orbit. The existing bank also fails a half-channel center-track coverage check
for one fixed conditional example. Spectra remain BLOCKED.** Twenty new targeted
tests pass. No telescope values, scientific controls or old holdouts were opened.

This completes the bounded physical-motion accuracy/coverage contract requested
at science commit `0af377cbb7b385b86c5951e6feeb6bcdbdf12be9`.
The [protocol](RADIO_MOTION_CONTRACT_2026-09-27_PROTOCOL.md) gives the mathematical
derivations, local freeze chronology, exact scope and exclusions.

## Corrected orbital interpretation

The retained small catalogue snapshot omitted limits and per-parameter sources.
New official solution rows and the original paper establish:

| Historical scalar | Provenance and meaning | Used by existing direct bank? |
| --- | --- | --- |
| P = 5.77152 +/- 0.00045 d | Díaz et al. 2016 | Yes |
| a = 0.0634 +/- 0.0022 AU | Díaz et al. 2016; relative orbit axis | Yes |
| e = 0.172 | Díaz et al. 2016; **99% upper credible limit**, not central e | Yes, as a conditional comparison value |
| T_per = 2450366.936 | Rivera et al. 2010 | No; the bank uses free phase |
| omega = -10 (+74/-56) degrees | Unique matching value/error/limit tuple in Rosenthal et al. 2021 among four retained PS rows; inferred provenance | Yes |

[Díaz et al., Table 5](https://arxiv.org/abs/1510.06446) gives 95%/99%
eccentricity upper limits 0.131/0.172 and leaves omega unconstrained. Its mean
longitude is 271.6 +/- 4.1 degrees at BJD 2455155.3854; the table does not establish
the time scale. The paper describes semimajor axes of relative orbits. The
primary PDF page 12 was rendered and visually checked; its SHA256 and factual
transcription are retained without republishing the paper/image.

The [NASA Archive column documentation](https://exoplanetarchive.ipac.caltech.edu/docs/API_PS_columns.html)
distinguishes per-solution `ps` rows from the potentially composite `pscomppars`
values and warns that literature omega conventions vary. The [current official
HD 1461 b listing](https://science.nasa.gov/exoplanet-catalog/hd-1461-b/) likewise
labels eccentricity as less than 0.172. The new retrieval on 27 September 2026
contains four publication-specific solution rows. All five scalar values still
agree exactly with the old snapshot; the correction concerns their meaning.

The complete snapshot combines three references; the bank's consumed P/a/e/omega
combine two. It is not a coherent central orbital solution. The old e=0.172
calculations remain valid conditional engineering comparisons, including the
old circular-versus-eccentric discrepancy. They do **not** establish that HD 1461 b
has eccentricity 0.172. No coordinate, parameter, bank or old result was changed
to make a model pass.

The new metadata audit refuses a missing/nonzero point-value flag, missing or
mixed references, unspecified time scale, omega body and relative-to-transmitter
axis conversion. A phase-agnostic policy correctly does not require T_per;
an epoch-anchored policy does. Even a complete metadata declaration grants no
physical-bank or spectral permission. This is a supplementary audit, not a
retroactive change to the old immutable execution envelope.

## Fixed-witness result for the unchanged bank

Use the historical P/a/e/omega scenario solely for this diagnostic. The witness
was fixed at projected scale 0.25 and phase 9/32, at 1500 MHz. Reuse the stored
33-template catalogue-coordinate bank and all existing scan times. Optimize
each template's physical carrier freely, which gives it more freedom than the
real carrier grid. Exact finite-time minimax geometry yields:

| Required ON support | Best maximum center discrepancy | Native channels |
| --- | ---: | ---: |
| All three ON epochs | 112.396874 Hz | 39.639125 |
| ON epochs 1 and 2 | 67.491007 Hz | 23.802125 |
| ON epochs 1 and 3 | 112.396874 Hz | 39.639125 |
| ON epochs 2 and 3 | 63.651018 Hz | 22.447872 |

Template 7 (scale 0.5, phase 0.375) is best in all four restrictions. The native
spacing is 2.835503418452676 Hz; the illustrative half-channel tolerance is
1.417751709226338 Hz. Each restriction exceeds that tolerance even with a free
carrier. Thus the unchanged bank does not cover the continuous scale/phase
domain at half-channel center accuracy under this conditional historical model.
The margin is much larger than the independent minimax numeric check tolerance
of 0.0000002 Hz. This is numerical, not interval-certified, evidence.

**This is not detector recovery failure.** Broad filters may include offset
tracks, and integrated support, signal power, noise and thresholds were not
evaluated. It is one counterexample, not four independent cases or a coverage
fraction. No new template, width, threshold or physical orbit is adopted.
All 132 distinct template/scope fits, free carriers, active row pairs, witness
factors and best residual vectors are retained. No old phase sweep was rerun.

## What can and cannot be bounded

A new analytical jerk/interpolation bound avoids another sampled phase audit.
For fixed central P/a, all phases and the **conditional** interval e in [0,0.172]:

| Conditional idealized quantity | Upper bound |
| --- | ---: |
| Speed norm | 142180.235194 m/s |
| Acceleration norm | 2.196371695 m/s² |
| Jerk norm | 0.000079529830245 m/s³ |
| Emitter-only linear interpolation, 17.986224128 s at 1500 MHz | 0.016098917 Hz |

The eccentricity condition is a deliberate mathematical restriction, not a
99% joint confidence statement. The exposure bound holds the observer factor
fixed and omits uncertain orbit parameters, clock transformation, relativistic
emitter/systemic terms and channel response. It cannot be used as a total error
certificate. The old radial-only relativistic comparison also remains only a
partial diagnostic; it does not supply the missing full correction.

The executable accuracy contract leaves all seven complete term bounds null:
pointing/observer, orbital domain/conventions, time mapping, relativistic
emitter/systemic motion, full exposure/instrument response, continuous-bank
coverage and numerical transfer. Scope-mismatched or unqualified sub-bounds
cannot be added into a misleading small total. Total status is `BLOCKED`.

Concrete missing physical information is now explicit: an adopted coherent
solution **or** prospective phase-agnostic uncertainty domain; omega/transmitter
and relative-axis conventions; masses or a justified mass-ratio bound; the
relevant source/observer time and frequency mapping; a complete relativistic
error allowance; and end-to-end width/recovery evidence over the declared domain.
A precise absolute T_per is not mandatory for an all-phase search. This work
does not invent such a solution/domain or infer one from marginal errors.

## Validation, resources and preserved state

Twenty tests cover the new metadata/limit risks, independent 60-digit Decimal
minimax feasibility, carrier-grid relaxation, analytic circular jerk units,
exposure/frequency scaling and fail-closed partial/error budgets. Python 3.12.14
and NumPy 2.3.5 suffice; reproduction needs no astronomy/network package.
The unchanged stored observer/clock/bank artifacts are the inputs.

```sh
PYTHONPATH=src:scripts python scripts/radio_motion_contract.py
sha256sum -c RESULTS_MANIFEST_RADIO_MOTION_CONTRACT_2026-09-27.sha256
```

`results_radio_motion_contract_2026-09-27/` retains raw NASA responses, all three
direct acquisition receipts, factual primary-paper transcription, provenance
audit, complete per-template fit summary, conditional bounds, blocked accuracy
contract, runtime hashes and test log. The checksum manifest covers new code,
configuration, protocol, result report and evidence.

The bounded direct artifact acquisition consumed **3 requests / 2,552,106
response bytes**, below its 8,912,896-byte ceiling, with no automatic retry.
Discovery/search response bytes were not instrumented and are outside this
artifact accounting. There were zero telescope requests or reservations, zero
new scientific trials and zero evaluation/holdout exposures. Local arithmetic
reproductions are not fresh cases. The closed 2048-phase audit, old control
panels, native pipeline and codec qualifications were not repeated as progress.

The original source contract SHA remains
`c434c6f0615dfec165512195dcae888d8aa4b33a29efdb5037895ba5530d8bcb`.
The closed, exhausted synthetic ledger SHA remains
`b77c59e4e1772b27ef7c170bb1c08d1f6c7483d1f12a6c5a0a0deedfca82fd83`.
The prospective telescope genesis remains empty. The execution envelope still
has seven preparation passes and the same five blockers; no original gate is
rewritten by this report. The prospective cumulative telescope caps remain
1.5 GiB / 1,500 requests / 3,600 seconds across three ordered roles, unactivated.

## Exact continuation

The bounded orbital-limit/reference investigation and single-witness check are
complete. Do not repeat the four archive rows, paper Table 5, witness or old
phase audit as new progress. The old e=0.172 bank must continue to be labelled
conditional engineering; do not silently substitute e=0 or e=0.062, expand the
bank, rerun/tune failed controls, or execute the frozen fresh 24-case panel.

The next independent engineering item is the **unimplemented remote v2 ledger
backend**, whose exact specification was frozen in
`results_radio_codec_publication_2026-09-27/publication_store_spec.json`.
Implement its pinned repository/branch/path and append-only protocol against
an injected GitHub service, and test stale head, competing writers, missing
ledger, response loss and read-back ancestry on isolated service fixtures.
Do not activate/create the telescope namespace, reset/reuse the exhausted
published demo, spend source budget, or claim live remote qualification from
mocked tests. A live qualification would need its own prospective isolated
namespace and budget; do not create either implicitly.

Physical qualification remains blocked by the named information above. Reopen
that branch only for a specific new input or an explicit, prospective domain
and convention contract; neither scalar catalogue refreshes nor more samples
close it. Pointing still requires a genuinely new same-scan original RAW/FIL
header, observing log or documented file-specific conversion for AGBT16A_999_189
ON scans 0015/0017/0019. No such new evidence was obtained here. HD 1461/HIP1499,
cadence 71139, stays selected under the 34.23-arcminute provenance hold.

M43AI stays failed/closed; original 112+128 M43AF holdouts remain untouched.
M15 GJ581 and M33 HD3651 remain unresolved, with all earlier dispositions.
LS is paused at LS8BD–LS8BE, LS8BF unopened, CHEOPS unsent. No messages, paid
services, booking, delegation or additional automation was used. The plan ends
with consolidation on **9 October 2026** and is not extended.
