# Independent pre-main review

**PASS: no remaining blocker in the reviewed scope.** The review independently reconstructed all 188 selected Gaia-associated objects and the exact development exclusions, then exercised nine final detector boundary cases. No main photometry was read.

[Gaia review](GAIA_REVIEW.json) recomputed 1,702,989 catalog/object pairs, stellar proper-motion covariance evidence, neighbor ambiguity guards, exact IDs, conservative development exclusions, main-counterpart deduplication and selection order. Maximum approximate Cartesian versus original propagation discrepancy was 1.86×10⁻⁸ arcseconds for nearest separations, with no threshold-count disagreement. Documented coordinate-epoch and catalog limitations remain.

[Detector review](DETECTOR_REVIEW.json) confirms the corrected distinct-visit rule. The earlier `(visit, detector)` count could admit fewer than five visits; the final code counts visit IDs and excludes ambiguous alternative-detector measurements. Synthetic controls verify rejection of four visits represented by five detector rows, exclusion of the entire tested UTC date and future samples, same-band context, required earlier dates, primary quality flags and the separately qualified forced stream. The actual development data contain no admitted cross-detector same-object/visit/band group, so that correction does not change their results.

Exact reviewed hashes and the combined conclusion are in [REVIEW_SUMMARY.json](REVIEW_SUMMARY.json). Independent development numerical and recovery audits are recorded separately by `rubin_main_audit`. These checks do not establish physical events, local quiescence, a calibrated false-alarm probability or a qualified 50-object sample.
