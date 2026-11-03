# Independent C016 joint arithmetic verification

C016 / R017 contains four **HD114386** records, original queue rows 27, 29, 30 and 32. Their exact discovery products and catalog coordinates remain separate:

| Record | Discovery product | Catalog barycentric center (Å) |
| --- | --- | ---: |
| V2E2-0094 | ADP.2022-03-08T01:01:37.348 | 4303.785 |
| V2E2-0096 | ADP.2022-05-17T01:02:16.724 | 4303.785 |
| V2E2-0098 | ADP.2023-01-03T01:08:17.803 | 4303.785 |
| V2E2-0110 | ADP.2023-08-29T01:02:07.487 | 4303.79 |

The fixed group center is the midpoint of the minimum and maximum catalog centers, **4303.7875 Å**. The first queue record, V2E2-0094 observed on **7 March 2022**, anchors the common topocentric coordinate with BERV **19.1606928163471 km/s**, giving **4303.512448784194 Å**. The seven exact HD114386 observing products span January 2022–August 2023 and **51.572001697156 km/s** in BERV. Earlier HD112410 or HD106515A cohorts and their numeric anchors are not transferred.

The group core remains ±0.25 Å about the fixed midpoint, **4303.5375–4304.0375 Å**. It differs from each original member core by **0.0025 Å** at the relevant edge. The original cores span 4303.535–4304.04 Å collectively; they are not declared identical to, or fully contained within, the common core. Original centers and member markers remain explicit. No new center, width, shift, continuum or background is fitted.

`independent_math.py` implements scalar interpolation using binary search, a signed pooled-flank median, first-difference MAD, common-support Pearson correlation and normalized RMS. It imports no production code. The 601-point grid has 51 group-core points and 550 surrounding points, with minimum common support of 41 and 440. Fixed flanks lie 1.5–3 Å from the frame center, require at least 20 finite samples each and retain the sign of the pooled reference.

`audit_prospective.py` verifies the exact target cohort, four distinct fixed references, midpoint rule, March anchor, all four 72-order native header scans, source bindings, unchanged numerical estimators and historical mapping stages. Each source is selected using its own original event center and BERV; the diagnostic uses the one common group anchor. Analytic flux on each fresh native polynomial checks geometric support without observational flux. Other synthetic fixtures distinguish missing coverage, insufficient finite support, zero or negative references, low positive references, gaps, nonfinite values, zero variance and exact support boundaries. Only this synthetic harness imports production functions as test subjects.

The planned native scope is one **order 19** context for each of the four distinct discovery products, with four historical raw panels. Every global-grid, original-local, original-baseline and later five-window mapping flag remains **true**, without changed registration. All four primary, secondary and root-adopted reviews retain **U**, with their separate original evidence for broad native features, neighboring structure and weak diffuse trace-associated enhancement. Source support, flux quality, reference validity, mapping history and physical origin remain distinct.

Every one of the seven merged epochs is compared with **all four fixed discovery references**, in both frames and both regions: **112 merged rows**. The four native contexts are compared only with their own same-exposure merged product, adding **16 rows**. The total is **22 profiles, 128 comparisons, 11 bounded source windows, four raw copies and 16 labelled identical-product self comparisons**.

For any one frame and region, the 24 nonself merged rows are four sets of six comparisons on the same seven observing epochs. Discovery-to-discovery comparisons include six reciprocal pairs; their directed source/reference identities remain explicit. These are dependent repeated comparisons, not 24 independent epochs, new observations or independent detections. Same-exposure native/merged agreement also shares extraction lineage.

After explicit root public release and production completion with a stable output ledger, `audit_actual.py --authorized-after-root-run` independently reconstructs all bounded inputs, profiles and pair arithmetic. It checks all source and output hashes, four raw byte identities, every reference relationship, reciprocal discovery pairs and exact prospective audit-source hashes. It imports no production functions. Missing, partial, raw-only, nonpositive-reference or low-positive-reference outcomes remain explicit if measured. Reports are one-shot outputs; a failed result is retained rather than replaced by an adjusted analysis.

Original HD114386 epoch/raw investigations and completed blue normalization contexts already used these observing products. The C016 window is disjoint from completed bounded group windows, but it is dependent post-detection work on prior observations. This audit verifies arithmetic and lineage; it adds no blind validation, calibrated uncertainty, qualified survey null, origin assignment, observing time, normalization-pipeline replay or classification change.
