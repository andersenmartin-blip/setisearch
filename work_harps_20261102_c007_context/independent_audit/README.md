# Independent C007 arithmetic verification

C007 is the singleton V2E2-0026 on HD106515A. Its seven existing merged epochs are compared against the one fixed discovery product; one native order 19 context and its one historical raw panel remain explicit. The core was already visible inside C006's positive reference flank, so this phase is not blind or independent validation.

`independent_math.py` independently implements scalar interpolation using binary search, a signed pooled-flank median, first-difference MAD, common-support Pearson correlation and normalized RMS. It imports no production code. The 601-point grid has 51 core points and 550 surrounding points, with minimum common support of 41 and 440.

`audit_prospective.py` verifies metadata geometry, input bindings, singleton accounting and unchanged estimators. Synthetic fixtures exercise gaps, nonfinite flux, missing flanks, nonpositive references, zero variance, frame transforms and exact support boundaries. Only this synthetic harness imports production functions as test subjects; it opens no observational arrays. The historical local/baseline mapping failures remain explicit alongside later global/five-window support.

After root release and completion of the production run, `audit_actual.py --authorized-after-root-run` reopens the exact source files, independently reconstructs eight bounded windows, all 16 profiles and all 32 comparisons, and verifies the exact historical raw copy. Four identical-product self comparisons remain labelled. This actual reconstruction imports no production functions. Reports are one-shot outputs and preserve any failure rather than substituting a later attempt.

These checks verify arithmetic and lineage consistency. They do not calibrate uncertainty, identify a physical line or origin, add observing time, change the U label, or treat repeated/overlapping spectral values as independent evidence.
