# Independent C002 arithmetic verification

C002 is the singleton V2E2-0033 on HD106515A. All seven existing merged epochs are compared against its one fixed discovery product. Native orders 2 and 3 and both historical raw panels remain explicit. The original core was already visible between C003's negative reference flank and core, outside those masks. It lies outside C004's window, while the wider C002 context overlaps C003 and C004. These overlapping values and reused observations are not blind or independent validation.

The discovery reference is **ADP.2022-05-08T01:01:37.876**, observed on 7 May 2022, with BERV **−18.8907517532076 km/s**. The common barycentric center is **3868.6025 Å** and the fixed topocentric center is **3868.846286702511 Å**. The May anchor is independently checked against the metadata.

`independent_math.py` implements scalar interpolation using binary search, a signed pooled-flank median, first-difference MAD, common-support Pearson correlation and normalized RMS. It imports no production code. The 601-point grid has 51 core points and 550 surrounding points, with minimum common support of 41 and 440.

`audit_prospective.py` verifies identity, metadata geometry, all 72 native header polynomials' endpoint coverage, exact input bindings, unchanged estimators and both historical mapping histories. Synthetic fixtures exercise gaps, nonfinite flux, missing flanks, nonpositive references, zero variance, frame transforms and exact support boundaries. Additional synthetic flux on header-derived order 2 coordinates verifies its geometric constraints; 19/20 finite-flank fixtures check the separate count gate. Only this synthetic harness imports production functions as test subjects. It opens no observational arrays.

Order 2 covers the original core but ends before the entire positive reference flank in both frames. Its broad grid support cannot reach 440 points; normalization is unavailable and raw core Pearson remains separately eligible if finite support and variation suffice. These coverage facts are separate from its historical global/local/baseline/five-window mapping flags of true/false/false/true. Order 3 has four true flags. Later mapping support does not rewrite earlier failures.

After root release and production completion, `audit_actual.py --authorized-after-root-run` reopens the exact source files and reconstructs nine bounded source windows, all 18 profiles and all 36 comparisons. Both historical raw copies are verified exactly; four identical-product self comparisons remain labelled. The actual reconstruction imports no production functions. Reports are one-shot outputs, retaining any failure rather than replacing a result with a later attempt.

These checks verify arithmetic and lineage consistency. They do not calibrate uncertainties, identify physical lines or origins, add observing time, change the U label, or treat shared spectral values and observations as independent evidence.
