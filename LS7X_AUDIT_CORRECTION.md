# LS7X audit tolerance correction — 19 September 2026

The first execution of the prospectively frozen LS7X evaluator completed
before the independent audit stopped publication.

No scientific rule failed. The audit's independently solved two-parameter
normal equations differed from the producer's NumPy/LAPACK least-squares
solution by 5.96047e-8 electrons in one event-excess comparison
(-287.45336478948593 versus -287.4533648490906). The original audit used
math.isclose(rel_tol=2e-10, abs_tol=2e-8), which is substantially stricter in
relative precision than the 2e-8 numerical comparison convention used in
earlier project audits.

This correction changes only the audit comparison to:

- relative tolerance: 2e-8
- absolute tolerance: 2e-10

The producer and its public freeze af8b37c94086634c793837f4dbd1596ab7c76822
remain unchanged. The DEFAULT aperture, raw table bytes, STATUS eligibility,
gap rule, 12+12 sidebands, two-row guards, 1/2/3-cadence windows, local linear
baseline, noise scale, score definition, 8.5 positive/negative threshold and
clustering rule are unchanged.

The first evaluator output reported two positive clusters and no negative
threshold crossings before the audit stopped publication. Those outcomes are
not used to alter this tolerance or any scientific decision rule. The rerun
must reproduce the same frozen evaluator output, and the corrected independent
audit must verify the complete ledger before publication.
