# METHODS64 report and figures: static peer review

Status: **PASS_STATIC_REPORT_AND_FIGURE_WORKFLOW**. The reviewed code is prospective preparation; this review does not assert that METHOD_STUDY has run, replace its complete retained-output audit, or authorize any telescope acquisition.

Reviewed files and SHA256:

- `pilot_method_study_20261008/build_method_report.py`: `f45ae90d64b313b817500e138b527ab71a4f9120a27909c3acc6cd0cc5f7a08e`
- `pilot_method_study_20261008/method_figures.py`: `ca8114d329140c56fa83bdddaf2ea271ed757a104c0d98ca592d9cc9fb0c0b12`

Before outcome loading, report generation or plotting imports, the main workflow requires both durable panel markers: complete 64-case exploratory METHOD_STUDY with qualification false and successful resource closure, and closed 142-case VAL_B failure with all children reaped. It then requires the independent audit status `PASS_INDEPENDENT_METHOD_STUDY_OUTPUT_AUDIT`, explicit independence, completeness, 64 expected/observed cases and qualification false. The audit must bind all ten input digests: method and B case banks, outcomes, summaries, resource receipts and completion markers. Marker aggregate digests must agree with current bytes. The exact frozen case-bank hashes are hard-coded. Missing/partial/failed methods cannot reach plotting.

The report recomputes the exact 64-cell grid, case identities/seeds, integrity-valid Boolean recovery responses, full and marginal descriptive totals, and original summary group counts. The revised report now exports the required level/drift/placement groups of 16 distinct cells and width/activity groups of 32, with valid/expected denominators and pre/final all-active and any-active counts. Their CSV, JSON and Markdown tables accompany the 64-cell records. Both original closed method and B summaries are retained unchanged in report data.

Figures separately show all-active and any-active final recovery. Exact binary cells are labeled one independent realization per cell, n=1. Each strength/drift marker is a count out of four distinct cells pooling the opposite factor at fixed activity/width; it is correctly labeled n=4 and is not presented as repeated draws at one setting. Numeric aggregate axes preserve actual factor positions; scatter markers have no connecting lines. Binary cell images use no interpolation. Local figure validation enforces the exact grid, complete denominators, explicit Booleans and aggregate/cell agreement before matplotlib imports.

The report preserves A and B FAIL_CLOSED, qualification false, no telescope values, post-B exploratory selection, independent noise across activity groups, different all/any recovery requirements, and placement limitations. It makes no calibrated probability, false-alarm, flux, sensitivity-curve or causal visit-effect claim. B invalid attempts remain separate from measured nonrecovery; noise recovery truth is shown as absent. Output directories are new and separate from retained panel evidence.

Review used source text and standard-library AST parsing only. No report/figure helper, scientific module, RNG, detector, codec, source reader or network call was executed. No numeric map, array or telescope value was read. Actual report rendering and its resource accounting remain future verification after the required closed audit.
