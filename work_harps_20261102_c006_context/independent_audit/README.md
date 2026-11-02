# Independent C006 arithmetic verification

This audit treats C006 as three catalog records from two distinct discovery products. It preserves the three historical raw panels while reconstructing native order 19 only once per product. The seven existing merged epochs are compared separately against both unique discovery products.

`independent_math.py` implements scalar interpolation using binary search, a signed pooled-flank median, first-difference MAD, common-support Pearson correlation and normalized RMS. It imports no production code. The fixed 601-point grid has 81 core points and 520 broader-pattern points; the corresponding 80% common-support gates are 65 and 416.

`audit_prospective.py` checks the exact metadata geometry, source hashes, unique-reference accounting and unchanged estimators. Synthetic fixtures exercise missing flanks, gaps and nonfinite flux, negative normalization references, zero variance, fixed-frame transforms and support boundaries. It imports the production functions only as the synthetic test subject and opens no observational arrays.

After the root authorizes the completed production run, `audit_actual.py --authorized-after-root-run` reopens the exact source files, independently reconstructs bounded slices and all 18 profiles/64 comparisons, and verifies all three preserved raw copies. It imports no production functions. It retains eight identical-product self comparisons, explicitly labeled. Audit reports are one-shot outputs and are never substituted for a failed attempt.

These checks establish arithmetic and lineage consistency. They do not calibrate uncertainty or significance, count overlapping records as independent evidence, identify a line, assign a physical origin, or change any U classification.
