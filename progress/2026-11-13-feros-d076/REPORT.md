# Current FEROS continuation: D076 completed, 2026-11-13

**This is the current scientific pointer, superseding the D075 continuation notice in PR #36.** The version-guarded project checkpoint already contained completed D075 and D076 when a final publication/save reconciliation found it. Its state must not be replaced by an older D075-only pointer. The D075 calculation prepared for PR #36 reproduces the same 900 forward order curves; it is a numerical replication on the same data, not a new independent experiment or another scientific phase.

## D076 result

D076 reverses which observation is the reference and which is the target, retaining all 240 existing merged/order profiles, all ten chronological epoch pairs, all three sites, extraction modes, flat/nonflat variants and all fixed masks. It adds **1,440 curves and 577,440 fixed-grid evaluations**. Every slot is supported, every fitted scale at the minimum is positive, and no minimum is on the grid boundary. The candidate core remains excluded.

At 0061 the maximum forward/reverse reciprocity residual is **0.95 km/s** over the predefined masks. One retained configuration (HDU 30, optimal extraction, flatfielded, RED mask, epochs F2/F4) gives **−0.90 km/s forward and +1.85 km/s reverse**. The additive log-coordinate sum should be zero for reciprocal shifts but is about 0.95 km/s here. This is distinct from the configuration giving the maximum 1.45 km/s order–merged difference in D075. The largest BOTH-mask reciprocity residual in the individual orders at 0061 is 0.15 km/s; the 0.95 maximum includes the one-sided masks.

Swapping the reference also changes which spectrum is interpolated, which receives residuals and which epoch supplies the target grid. This control therefore does **not isolate interpolation alone**. It documents protocol direction dependence on the same two observations, not a change in the star's motion. No direction-averaged best velocity is manufactured.

The residual is c*[atanh(v_forward/c)+atanh(v_reverse/c)], c=299792.458 km/s. The unchanged grid has 401 nodes from −10 to +10 km/s. **The 0.05 km/s grid step is not physical precision**, and no noise-calibrated acceptance threshold, sigma, uncertainty or FAP is defined.

## Verified scope

The retained D076 alternate audit checked all **577,440 grid nodes**, 1,440 reverse masks/source-role swaps, 1,440 reciprocity pairs, 1,740 other pair differences and 1,440 reverse three-epoch closures. All computed minima were reproduced; the largest independent SSE discrepancy was 1.11e-10. D075 and D076 together retain 2,340 curves and 938,340 grid fits. These are internal alternate calculations by the same assistant, not external peer review.

The current completed state contains **105,681 table cells** in the same 37+141 rows. All 102,833 pre-D075 cells, the original candidate statistics and every previous failure/status flag are preserved. D075 alone remains a historical 104,257-cell overlay. No new candidate statistic is shifted or reclassified by either analysis.

**0 qualified lasers; all three previously investigated physical origins remain unresolved.** No absolute stellar RV, physical rest frame, covariance, laser response or persistence exclusion is validated. The FEROS controls use 2019 observations; they are not simultaneous confirmation of the original 2021 events.

## Next prospective gate: D077

D077 remains **proposed, not frozen or executed**. Its scope is a metadata/provenance gate for all **30 exact WLC raw references** already declared by the five existing calibration chains. Confirm archive identity, dates, instrument/configuration, fiber/illumination labels, units and access for every reference, retaining missing/mismatched inputs. Calibration pixels, wider stellar templates and new line catalogues require separately declared input/numerical gates. No selection after inspecting the local minima, and no application of D074–D076 shifts to candidate statistics.

See [SUMMARY.json](SUMMARY.json), [METHOD.json](METHOD.json), [NUMERICAL_AUDIT.json](NUMERICAL_AUDIT.json), and the [D075 historical result](../2026-11-13-feros-d075/REPORT.md). Public ESO source identifiers remain in D075/SOURCES.json. The complete extraction/array chain is retained in project checkpoints and is not made self-contained by this text publication. No telescope payload, binary evidence archive or private storage identifier is included. The separate historical 663-file delivery remains pending.

The old 141 raw queue stays closed, the 90/Rubin track stays stopped, and no background science job is running.
