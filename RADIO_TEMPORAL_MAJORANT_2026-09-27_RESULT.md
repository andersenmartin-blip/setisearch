# Conditional temporal compression and integrated disposition — 27 September 2026

**Fourteen new tests pass. The same conditional retarded emitter tracks admit
degree-5 and degree-6 temporal representations with uniform remainder bounds
below half a native channel. No polynomial, template or search bank was made.**

This completes the connected domain, timing, covering and temporal-representation
investigation: **58 distinct new tests**, across four separately bounded packages.
The previous three packages were published and verified before proceeding here.
This result follows science `5ef2667a1aa24bf79a8b2dc6373efea7204121ac`.
The [protocol](RADIO_TEMPORAL_MAJORANT_2026-09-27_PROTOCOL.md) derives the
uniform derivative majorants and gives the exact arithmetic and scope.

## Uniform conditional remainder result

At received reference frequency 1500 MHz and |s|<=1960.7864736412732 seconds,
the six prospectively fixed polynomial degrees give these **upward-rounded**
upper bounds. They describe representation by the model's actual reference
derivatives, not fitted coefficients or an adopted polynomial search.

| Degree | Remainder upper bound (Hz) | Within illustrative 1.417751709226338-Hz tolerance? |
| --- | ---: | --- |
| 1 | 794.675536943186399 | No |
| 2 | 288.002844230887918 | No |
| 3 | 31.921799605425497 | No |
| 4 | 3.756235772564436 | No |
| 5 | 0.458764710471825 | Yes |
| 6 | 0.057497817768524 | Yes |

An upper bound above tolerance does not prove that a lower-degree approximation
fails for every orbit, or even that no tighter bound exists. Degrees 5/6 are
sufficient for *conditional temporal representation*, not proof of a feasible
coefficient bank or detector recovery. The tolerance is a reporting yardstick,
not a changed detector gate. No order beyond six, parameter optimization,
coefficient search, template generation or spectral evaluation was performed.

The bounds hold for every phase/orientation in the already declared P/a/e and
COM-axis relaxation, under the same stationary-receiver, fixed-LOS, flat-spacetime
proper-oscillator assumptions. Reception time includes varying orbital delay.
They omit observer/systemic/gravitational transformations, real clock-scale
mapping, other emitter motion and instrument response. Real-source membership
and the total physical error remain unknown; no joint probability is inferred.

Unlike the earlier binary64 diagnostics, this coefficient calculation uses
**exact rational majorants and one-sided pi/square-root enclosures**. Every
coefficient, inverse-time term, normalization bound and remainder is retained as
an exact numerator/denominator pair in
[remainder_certificate.json](results_radio_temporal_majorant_2026-09-27/remainder_certificate.json).
Machin's alternating-series bounds and integer square-root bounds support all
irrational substitutions. This certifies finite arithmetic under the documented
analytic inequalities, not the actual source, old implementation or a formal
theorem-prover proof. Finite-order Taylor remainder follows from uniform local
derivative bounds; no global power-series convergence is assumed.

## Validation and accounting

Fourteen new tests cover exact Machin identity, alternating enclosures,
integer-root bounds, binomial coefficients, independent Catalan inverse
coefficients, composition cross terms, circular norm/factorial limits,
independent first-three reception derivatives, zero-axis constancy, exact
tolerance comparisons, outward decimals and refusal of unplanned orders or
physical permissions. One qualification run retains all source/configuration
snapshots, logs and runtime. Test sockets were disabled. All 22 pinned prior
inputs match. Repeated evaluation of the same six-order certificate is not
counted as new cases or scientific trials.

```sh
PYTHONPATH=src:scripts python scripts/radio_temporal_majorant_qualification.py
sha256sum -c RESULTS_MANIFEST_RADIO_TEMPORAL_MAJORANT_2026-09-27.sha256
```

Across all four packages there were **zero** new catalogue/source requests,
telescope reservations, spectra, templates, polynomial tracks, scientific
trials, evaluation exposures or changes to existing detector settings. The
58 distinct tests comprise 16 domain/convention, 15 time/Doppler, 13 covering
and 14 temporal-majorant checks; they do not reuse closed tests as new progress.

## What transfers to the existing execution protocol

The [integration disposition](results_radio_temporal_majorant_2026-09-27/integration_disposition.json)
reads seven pinned existing protocol/resource artifacts without executing them.
It verifies the same five blockers, empty telescope genesis, unchanged attempt
limits and null full-accuracy total. The following distinctions are binding:

| New result | Permitted use | What it does not establish |
| --- | --- | --- |
| Conditional domain/conventions | Explicit mathematical support and meanings for future engineering | Actual HD1461 support, probability or adopted physical bank |
| Time/Doppler study | Quantify omitted terms when comparing the old emitter approximation with the declared retarded model | A complete physical error allowance or observer/time transform |
| Six-parameter covering study | One sufficient construction and its impractical dense cost | A required minimum size, instantiated bank or measured runtime |
| Rational temporal remainder | Uniform representability of the conditional model with bounded truncation | Coefficient quantization/coverage, bank identity, channel response, widths or recovery |

The 43.833105-Hz old-versus-new conditional emitter comparison and the new
0.458765/0.057498-Hz polynomial remainders concern different approximations.
The remainder does **not** bound the unchanged old first-order factor pipeline.
Nor may these partial numbers be presented as a complete physical error budget.
A future implementation of the retarded model would need its own identity,
finite bank/coverage, arithmetic/runtime and end-to-end evidence.

The existing fresh panel is explicitly `synthetic-prospective`: three calibration
identities and 24 fixed recovery/RFI/null cases. It is frozen, unexecuted and
unauthorized. Its identities, widths, powers, association rule and gates were
not changed. The mere existence of those cases cannot establish coverage of
the new six-coordinate domain or a future polynomial/coefficient bank. Any
future integrated freeze must bind the actual selected method and fresh,
disjoint roles before outcomes, without granting new attempts or tuning failures.

The exact calibration/validation/pilot windows and all 18 decoded payload
identities remain unchanged. Adjacent spectral windows remain separate payloads,
not independent observing realizations. Cumulative source caps remain
1,610,612,736 bytes, 1500 requests and 3600 seconds across the same three ordered
roles, with **zero reservations**. Scientific caps remain three calibration
realizations, one evaluation run of 24 cases, zero remedy attempts and zero
pilot runs before all gates. None of these allowances has been activated.

The original source preparation stays blocked and byte-identical; the published
synthetic acquisition ledger stays closed/exhausted and is not reset. The
envelope identity remains
`4f4fc7f477e1f0617632a314a99d95f719d17943ea294700559be675590593f6`.
Primary remains neighbor9. M43AI is failed/closed; original 112+128 M43AF
holdouts stay untouched, M15 GJ581 and M33 HD3651 unresolved. LS remains paused
at LS8BD–LS8BE, LS8BF unopened and CHEOPS unsent.

## Exact continuation and information frontier

This four-part conditional investigation is complete. Do not repeat the checks,
add degrees, instantiate/optimize the huge grid or create another arbitrary
parameter rectangle as routine continuation. No unblocked telescope-execution
step is established by these mathematical results. Progress on the actual
HD1461 pilot now needs concrete evidence in the existing unresolved boundaries:

1. **Pointing:** genuinely new same-scan original RAW/FIL header, observing log
   or documented file-specific conversion for AGBT16A_999_189 ON 0015/0017/0019.
   The known operator-log sign-on requirement and closed catalogue/public-code
   searches are not new evidence; do not repeat them without a new lead.
2. **Physical applicability:** evidence-backed source support and a coherent
   source/observer clock/frame mapping, emitter-location assumption, systemic/
   gravitational and instrument allowances. This conditional COM/flat-frame
   study does not supply them. Reopen a method study only for a specific input
   or a concrete remaining implementation risk with an explicit prospective
   scope, not another unconstrained sweep.
3. **Live acquisition engineering:** a concrete independently durable admission
   and provisioning capability with transport bounds, or an explicit prospective
   alternative preserving the frozen contracts. Do not recreate the closed
   self-funding bootstrap loop or relabel fixtures as live qualification.

After those inputs, a genuinely integrated prospective protocol must bind the
qualified finite motion/width bank, exact windows, fresh disjoint identities,
runtime/codec and cumulative budgets. Positive receipt handoff, numeric transfer
and recovery/RFI/null gates still have to pass in their declared order before
pilot spectra can be assessed. Do not correct coordinates, select another target
or open the unexecuted panel to compensate for missing information.

HD1461/HIP1499 cadence 71139 remains under the 34.23-arcminute pointing hold.
No external message, booking, paid service, delegation or new automation was
used. This is an interim information frontier, not a completed radio pilot or
an early period review. Consolidation remains scheduled in the plan for
**9 October 2026**; the two-week plan is not extended.
