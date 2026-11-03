# Independent C018 joint arithmetic verification

C018 / R019 contains seven **HD114783** records. All seven observing epochs are distinct discovery references, and every exact catalog center remains separate:

| Record | Discovery product | Catalog barycentric center (Å) |
| --- | --- | ---: |
| V2E2-0114 | ADP.2022-01-22T01:09:14.958 | 3869.3349999999996 |
| V2E2-0119 | ADP.2022-02-06T01:07:28.382 | 3869.3325 |
| V2E2-0124 | ADP.2022-05-06T01:04:00.123 | 3869.3325 |
| V2E2-0128 | ADP.2023-01-17T01:07:48.581 | 3869.335 |
| V2E2-0133 | ADP.2023-03-23T01:02:04.833 | 3869.3349999999996 |
| V2E2-0134 | ADP.2023-05-16T01:01:18.574 | 3869.3325 |
| V2E2-0138 | ADP.2023-07-02T01:01:43.311 | 3869.335 |

The fixed common center is the midpoint of the minimum and maximum catalog centers, **3869.33375 Å**. The first original-queue record, V2E2-0114 observed on **21 January 2022**, anchors the common topocentric coordinate with BERV **29.658729150824 km/s**, giving **3868.9509913064876 Å**. The seven exact HD114783 products span January 2022–July 2023 and **59.073251754930496 km/s** in BERV. Other target cohorts and numeric anchors are not transferred.

The common core remains ±0.25 Å about the fixed midpoint, **3869.08375–3869.58375 Å**. Its relevant edges differ from the original member cores by approximately **0.00125 Å**. All exact member centers, core bounds and discovery markers remain explicit; the common comparison mask is not widened or described as the complete union of original cores. No center, shift, width, continuum or background is fitted.

`independent_math.py` uses scalar binary-search interpolation, a signed pooled-flank median, first-difference MAD, common-support Pearson correlation and normalized RMS. It imports no production code. The 601-point grid has 51 common-core points and 550 surrounding points, with exact minimum common support of 41 and 440. Fixed flanks lie 1.5–3 Å from the frame center and require at least 20 finite samples each. Missing coverage, insufficient finite support, nonpositive pooled reference and a low positive reference retain distinct outcomes.

`audit_prospective.py` independently checks all seven reference identities, exact target-specific epochs, common-anchor and midpoint rules, original member coordinates/markers, source bindings, unchanged numerical estimators and all **504 native header rows**. It checks cubic wavelength monotonicity directly and selects each source using its original event center and own BERV. Analytic flux on every selected native polynomial then tests its actual common-frame geometry without opening observational arrays. Other fixtures exercise gaps, nonfinite values, zero variance, support boundaries and signed references. In particular, a negative individual flank with a positive pooled median remains usable under the fixed rule; a nonpositive pooled median is blocked, while a negative available flank with missing opposite coverage retains the coverage failure and is not normalized. Only the synthetic harness imports production functions as test subjects.

The expected native scope is **orders 2 and 3 for all seven products**: fourteen contexts and fourteen preserved historical raw panels. Fresh headers determine each frame's exact support. Order 2 is expected to retain the complete common core while lacking the right flank and sufficient broad support; it remains present as raw-only. Order 3 geometrically covers the complete context and both flanks. Geometric support is distinct from measured finite flux, reference signs and quality.

Historical mapping stages remain separate. For every order 2, global grid support is true, original local usability and original baseline verification are false, and later five-window support is true. Every order 3 retains all four flags true. Registration remains unchanged. Later support does not retroactively repair the original failed stage.

Six batch03 records have original primary/secondary/adopted **U/U/U**. **V2E2-0128 differs:** original primary **I**, original secondary **M** normalized to **I**, and adopted baseline **I**, followed by later unchanged-coordinate mapping support, later primary/secondary **U/U** and current **U**. Those original pixels, coordinates, source provenance and stages remain preserved. Current U labels describe unresolved structure and do not assign a physical origin. The remote bright deposit described for V2E2-0134 is not reassigned to its central candidate.

Every merged epoch is compared with **all seven fixed references**, in both frames and regions: **196 merged rows**. Each of the fourteen native contexts is compared only with its own same-exposure merged product, adding **56 rows**. Totals are **42 profiles, 252 comparisons, 21 bounded input windows, fourteen raw copies and 28 labelled identical-product self comparisons**. For any one frame and region, the 42 nonself directed merged rows represent **21 reciprocal observation pairs on seven observations**, with six other epochs per reference. They are not 42 independent epochs or detections.

After explicit root public release and a completed run with a stable numerical ledger, `audit_actual.py --authorized-after-root-run` independently reconstructs every bounded input, profile and pair. It verifies source/output hashes, fourteen raw byte identities, reference and reciprocal accounting, original mapping/history stages and exact prospectively frozen audit sources. It imports no production functions. All partial, raw-only, negative-reference, low-positive-reference and support failures remain explicit if measured. Reports are one-shot outputs; failures are retained rather than replaced by adjusted analysis.

Original C018 epoch/profile/raw evidence and the completed wider mapping diagnosis for V2E2-0128 already used these observations. Numerical overlaps with C015 and older HD114386, HD112410 or HD106515A blue windows share no source pixels because those are other targets and observing products. This is dependent post-detection work, adding no blind validation, independent observing time, calibrated uncertainty, qualified survey null, origin assignment, mapping/normalization replay or classification change.
