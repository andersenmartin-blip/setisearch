# Independent C010 arithmetic verification

C010 is the singleton V2E2-0086 on **HD112410**, original queue row 23 / R011. This changes target and observing cohort from the preceding HD106515A phases. The seven exact existing HD112410 products span April–August 2025 and **21.30284860830273 km/s** in BERV. Their original epoch/profile and raw investigations already exist; these are reused archival observations, not seven new observations.

The sole fixed discovery reference is **ADP.2025-04-30T01:01:50.866**, observed on **29 April 2025**, with BERV **3.40485846065643 km/s**. The exact catalog barycentric center is **3823.0649999999996 Å**. The wavelength-specific fixed topocentric center is **3823.0215804708346 Å**, recomputed as that exact float divided by `1 + BERV/299792.458`; no HD106515A product or numeric anchor is transferred.

`independent_math.py` implements scalar interpolation using binary search, a signed pooled-flank median, first-difference MAD, common-support Pearson correlation and normalized RMS. It imports no production code. The 601-point grid has 51 core points and 550 surrounding points, with minimum common support of 41 and 440.

`audit_prospective.py` checks the exact target-specific cohort, singleton identity, fixed geometry, all 72 native header polynomials, source bindings, unchanged estimators and historical mapping stages. Synthetic fixtures exercise gaps, nonfinite flux, missing flanks, nonpositive references, zero variance, frame transforms and exact support boundaries. Analytic flux on header-derived order 1 coordinates checks geometric coverage; separate 19/20 finite-flank fixtures check the finite-count gate. Only this synthetic harness imports production functions as test subjects. It opens no observational arrays.

Historical order 1 retains **global grid true, original local usable false, original baseline verified false and later five-window support true**. A fresh exact-header scan is checked independently rather than inheriting a covering-order decision. Geometric coverage is distinct from finite flux, positive reference levels and usable comparisons. The later supported mapping diagnostic does not repair the original local/baseline limitations.

Primary, secondary and root-adopted reviews all retain **U** for broad, diffuse trace-confined spectral structure without an unambiguous compact charge deposit. These agreeing U reviews and the unresolved qualification remain exact. No C009 A/A/U disagreement or artifact/spectral-blend text is transferred to C010.

After root release and production completion, `audit_actual.py --authorized-after-root-run` reopens exact sources and reconstructs eight bounded source windows, all 16 profiles and all 32 comparisons. It verifies the historical raw copy exactly and retains four labelled identical-product self comparisons. The actual reconstruction imports no production functions. Reports are one-shot outputs; failures are retained rather than replaced by an adjusted analysis.

These checks verify arithmetic and lineage consistency. They do not calibrate uncertainties, identify physical lines or origins, add observing time, alter the U label or turn original data into blind or independent observing evidence.
