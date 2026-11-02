# Independent C004 arithmetic verification

C004 contains V2E2-0028, 0045 and 0052 on HD106515A. All seven existing merged epochs are compared against all three unique discovery products. Three native order 3 contexts and three historical raw panels remain explicit. Its original core was already visible in C003's positive reference flank; the overlapping values and reused observations are not blind or independent validation.

The first discovery reference is **V2E2-0028 / ADP.2022-03-08T01:01:37.342**, observed on 7 March 2022, with BERV **10.77158288517 km/s**. The common barycentric center is **3872.245 Å**. The anchor is independently checked against the metadata rather than inherited from the January reference used in previous groups.

`independent_math.py` implements scalar interpolation using binary search, a signed pooled-flank median, first-difference MAD, common-support Pearson correlation and normalized RMS. It imports no production code. The 601-point grid has 51 core points and 550 surrounding points, with minimum common support of 41 and 440.

`audit_prospective.py` verifies group identity, metadata geometry, covering orders, exact input bindings, unchanged estimators and all three historical mapping histories. Synthetic fixtures exercise gaps, nonfinite flux, missing flanks, nonpositive references, zero variance, frame transforms and exact support boundaries. Only this synthetic harness imports production functions as test subjects; it opens no observational arrays. Original global/local/baseline/five-window mapping gates are true for all three records and are preserved without a new mapping claim.

After root release and completion of production, `audit_actual.py --authorized-after-root-run` reopens the exact source files and reconstructs ten bounded source windows, all 20 profiles and all 96 comparisons. Three historical raw copies are verified exactly; twelve identical-product self comparisons remain labelled. The actual reconstruction imports no production functions. Reports are one-shot outputs, retaining any failure rather than replacing a result with a later attempt.

These checks verify arithmetic and lineage consistency. They do not calibrate uncertainties, identify physical lines or origins, add observing time, change the U labels, or treat shared spectral values and observations as independent evidence.
