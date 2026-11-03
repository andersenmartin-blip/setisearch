# Independent C019 joint arithmetic verification

C019 contains five **HD114783** records and fixed discovery references:

| Record | Discovery product | Catalog barycentric center (Å) |
| --- | --- | ---: |
| V2E2-0115 | ADP.2022-01-22T01:09:14.958 | 3881.6125 |
| V2E2-0120 | ADP.2022-02-06T01:07:28.382 | 3881.615 |
| V2E2-0125 | ADP.2022-05-06T01:04:00.123 | 3881.6150000000002 |
| V2E2-0129 | ADP.2023-01-17T01:07:48.581 | 3881.615 |
| V2E2-0135 | ADP.2023-05-16T01:01:18.574 | 3881.6125 |

The fixed common center is the midpoint of the minimum and maximum exact catalog centers, **3881.6137500000004 Å**. The first original-queue discovery, V2E2-0115 observed on **21 January 2022**, anchors the common topocentric coordinate with BERV **29.658729150824 km/s**, giving **3881.2297765555622 Å**. The seven exact HD114783 products span January 2022–July 2023 and **59.073251754930496 km/s** in BERV. Five are discovery references; the other two epochs remain in every merged comparison set.

The common core remains ±0.25 Å about the midpoint, **3881.3637500000004–3881.8637500000004 Å**. Its relevant edges differ from the original member cores by about **0.00125 Å**. Exact member centers, original core bounds and discovery markers remain separate, including the floating-point distinction between 3881.615 and 3881.6150000000002. No common mask is widened and no center, shift, width, continuum or background is fitted.

`independent_math.py` implements scalar binary-search interpolation, a signed pooled-flank median, first-difference MAD, common-support Pearson correlation and normalized RMS. It imports no production code. The 601-point grid has 51 common-core points and 550 surrounding points, with exact minimum common support of 41 and 440. Fixed flanks lie 1.5–3 Å from the frame center and require at least 20 finite samples each. Missing coverage, insufficient finite support, nonpositive pooled references and low positive references remain distinct outcomes.

`audit_prospective.py` checks all five reference identities, the exact seven-epoch cohort, common anchor and midpoint rules, original member coordinates/markers, source bindings, unchanged numerical estimators and all **360 native header rows**. It independently checks cubic monotonicity and covering-order selection using each member's own original coordinate and BERV. Analytic flux on every selected native polynomial then tests the common-frame geometry without opening observed arrays. Other fixtures exercise gaps, nonfinite values, zero variance, support boundaries and signed-reference edge cases. A negative individual flank with a positive pooled median remains usable under the fixed rule; a nonpositive pooled median is blocked; a negative available flank with missing opposite coverage retains the coverage failure and is not normalized. Only this synthetic harness imports production functions as test subjects.

Fresh headers select **orders 3 and 4 for all five native products**. All twenty native frame contexts geometrically cover the complete core, window and both flanks. Geometry does not establish finite flux, positive references or comparison quality. All ten original global-grid, local and baseline mapping stages remain **true**, without changed registration. Four batch03 events explicitly retain later five-window support true. The older **V2E2-0129** has no such field and was not selected for that later follow-up, so its later support remains **null/unassessed**, neither false nor retroactively true.

All five records retain original primary/secondary/adopted **U/U/U** and current **U**, including older raw-followup V2E2-0129. Its original baseline containers remain preserved. The separate C018/0128 I/M history, order-2 limitations and later mapping diagnosis do not apply. The remote off-trace pixel described for V2E2-0135 does not classify its central diffuse feature. Mapping support and morphology do not assign a physical origin.

Every merged epoch is compared with **all five fixed references**, in both frames and regions: **140 merged rows**. Each of the ten native contexts is compared only with its own same-exposure merged product, adding **40 rows**. Totals are **34 profiles, 180 comparisons, 17 bounded input windows, ten original raw copies and twenty labelled identical-product self comparisons**.

For any one frame and region, five references each compare with six other epochs. The **30 directed nonself rows** represent **20 unordered observation pairs**, including **ten reciprocal reference pairs**, on seven observing epochs. Rows and pairs are dependent; neither count represents independent detections or additional observing time. Every directed source/reference identity remains explicit.

After explicit root public release and a completed run with a stable output ledger, `audit_actual.py --authorized-after-root-run` independently reconstructs every bounded input, profile and pair. It verifies source/output hashes, ten original raw byte identities, reference/reciprocal accounting, original mapping/history stages, unknown later fields and exact prospectively frozen audit sources. It imports no production functions. Partial, raw-only, negative-reference, low-positive-reference and support failures remain explicit if measured. Reports are one-shot outputs; failures are retained rather than replaced by adjusted analysis.

C019 and C018 reuse seven observing products and some identical native products, with disjoint newly bounded ±3 Å spectral windows. No independence of complete historical raw cutouts is inferred. Numerical overlap with older C005 uses another target and shares no observing products or source pixels. Original C019 epoch/profile/raw evidence already exists. This audit verifies arithmetic and lineage without adding blind validation, independent observations, calibrated uncertainty, a qualified survey null, origin assignments, mapping/normalization replay or classification changes.
