Perform one final, separately frozen background-estimator sensitivity check for V2E2-0235, then close this continuation with the event still **U**. The purpose is to measure dependence on the known outer-band asymmetry. It cannot identify fiber-B contamination or distinguish photon and charge origins.

The only two variants are:

| Variant | Per-row background estimator |
|---|---|
| Negative side | Median of the existing native pixels with −12 ≤ true cross-dispersion offset ≤ −9 |
| Positive side | Median of the existing native pixels with +9 ≤ true cross-dispersion offset ≤ +12 |

Use only the exact 8,275 pixels saved by the completed first run. Do not reopen additional detector rows, columns, raw products or epochs. Bind the saved-pixel archive and parent plan/result hashes before execution.

For each variant, retrain one **pooled** template using the same 232 training rows, signed background-subtracted normalization, fixed common grid and inherited validity requirements. Evaluate the same eleven target rows and eight eleven-row held-out controls. Preserve the header-polynomial trace, orientation, interpolation, fit mask, unconstrained one-parameter amplitude fit, on/off-band boundary and all metric definitions. The background choice must be applied consistently in that variant's training and evaluation. Do not add flank-only variants, a free target background intercept, slope, target shift, width adjustment, clipping or alternate masks.

Report both variants, including every failed normalization or blocked window. Exactly two variants × nine windows give eighteen accounted slots. Compare each with the closed pooled result using the same metrics, signed maps and target/control intensity context. Do not select the more favorable variant or declare a winner. Three pixels per side provide an estimator sensitivity test, not a reliable noise calibration.

If the near-trace mismatch persists, describe robustness to these two background choices. If it changes materially, describe estimator sensitivity. In either case, do not infer an origin, significance, physical photon fraction or a corrected spectrum. Preserve the completed first run and its interpretation. After this check, archive 0235 as unresolved with no further estimator or morphology variants in this continuation, and return to the broader fixed unresolved queue and evidence consolidation.

This contract is prospective. Root must publish the exact separate plan/code and release it before running the saved-pixel calculation. No execution is performed by this document.
