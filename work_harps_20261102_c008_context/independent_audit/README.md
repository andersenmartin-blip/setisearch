# Independent C008 arithmetic verification

C008 is the singleton V2E2-0047 on HD106515A. All seven existing merged epochs are compared against its one fixed discovery product. A fresh scan of all 72 native header polynomials selects only order 43, whose historical raw panel remains explicit. The ±3 Å window is disjoint in wavelength from completed C001–C007 bounded contexts, but original epoch/profile and raw evidence already exists and all seven observing products are reused. This is not blind or independent observing evidence.

The discovery reference is **ADP.2023-03-23T01:02:04.831**, observed on 22 March 2023, with BERV **3.26509772194068 km/s**. The common barycentric center is **5182.005 Å** and the fixed topocentric center is **5181.9485623946 Å**. The March 2023 anchor is independently checked against exact metadata.

`independent_math.py` implements scalar interpolation using binary search, a signed pooled-flank median, first-difference MAD, common-support Pearson correlation and normalized RMS. It imports no production code. The 601-point grid has 51 core points and 550 surrounding points, with minimum common support of 41 and 440.

`audit_prospective.py` verifies singleton identity, fixed metadata geometry, all 72 native header polynomials' endpoint coverage, source bindings, unchanged estimators and historical mapping stages. Synthetic fixtures exercise gaps, nonfinite flux, missing flanks, nonpositive references, zero variance, frame transforms and exact support boundaries. Analytic flux on header-derived order 43 coordinates tests its complete geometric coverage; 19/20 finite-flank fixtures separately check the finite-count gate. Only this synthetic harness imports production functions as test subjects. It opens no observational arrays.

Order 43 geometrically covers the complete fixed ±3 Å window and both flanks in both frames. Actual finite-flux support, reference sign and noise remain unknown before release. Its original global/local/baseline/five-window mapping flags are all true and remain unchanged; the audit does not establish a new registration.

After root release and production completion, `audit_actual.py --authorized-after-root-run` reopens the exact source files and reconstructs eight bounded source windows, all 16 profiles and all 32 comparisons. The historical raw copy is verified exactly; four identical-product self comparisons remain labelled. The actual reconstruction imports no production functions. Reports are one-shot outputs, retaining any failure rather than replacing a result with a later attempt.

These checks verify arithmetic and lineage consistency. They do not calibrate uncertainties, identify physical lines or origins, add observing time, change the U label, or turn shared observations into independent evidence.
