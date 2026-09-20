# LS8E — independent CHEOPS target/product selection protocol

Status: **FROZEN BEFORE NEW-TARGET SCIENCE VALUES**.

LS8D closes the eight retained 55 Cnc event branches. LS8E starts a new
independent optical search and must not select a target from prospective
light-curve or image outcomes.

## Frozen target order

Reuse the exoplanet-host order that was already published for the earlier
SETIsearch target programme. Do not reorder it using CHEOPS results:

1. GJ 876
2. HD 219134
3. GJ 514
4. GJ 849
5. GJ 649
6. HD 147379
7. 55 Cnc — excluded because LS7R–LS8D already used this system
8. 47 UMa
9. HD 48948
10. rho CrB

The first non-excluded host satisfying every CHEOPS metadata requirement below
is selected. If none qualifies, publish that obstruction rather than adding a
new target ad hoc.

## Metadata-only eligibility

Use the public CHEOPS/DACE visit database and product browser only. No product
download method is permitted during target selection.

A visit is eligible only when all of the following are true:

- public/published visit metadata;
- archive revision V0300 / processing chain 14.1.2 when represented by the
  published file key;
- public corrected light curve is available;
- positive finite exposure metadata and stacked exposure <= 60 seconds;
- the exact visit product inventory contains a DEFAULT `SCI_COR_Lightcurve`,
  `SCI_CAL_SubArray` and `SCI_COR_SubArray`.

A host is eligible only if at least **two distinct visits** satisfy all visit
requirements. Within the first eligible host, select the **two chronologically
earliest** eligible visits. Product availability and visit chronology are
metadata; do not inspect FITS table rows, fluxes, event scores, image arrays,
movies or diagnostic products to choose the target.

Target-name matching may use only the fixed spelling and whitespace-free alias
for each frozen host (for example `HD 219134` and `HD219134`). Duplicate
query rows or archive versions are deduplicated by exact file key.

## Outputs and hard boundary

Save every target query result needed to reproduce the decision, every checked
visit's product-name inventory, the complete eligibility ledger and the
mechanically selected pair. Record explicitly:

- selected target and fixed target rank;
- file keys, OBSIDs, visit IDs and chronology;
- exposure metadata and pipeline/revision metadata;
- required-product presence;
- rejected target/visit reasons;
- **science product bytes read = 0**.

Before any selected L2 table value is opened, publish this metadata result and
freeze a separate cadence-screen protocol. That later screen must preserve
symmetric positive/negative controls and must not treat a score as Gaussian
significance. Any image follow-up requires another separately frozen scope.

Do not reopen 55 Cnc, unused TESS sectors or M43 held-out panels through LS8E.
The raw-imagette calibration gate remains a separate NOT_READY branch.

[Previous closure](LS8D_CONTINUATION.md)
[LS8D result](results_ls8d_images/REPORT.md)
