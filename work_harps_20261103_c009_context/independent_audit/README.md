# Independent C009 arithmetic verification

C009 is the singleton V2E2-0050 on HD106515A, original queue row 18 / R010. All seven existing merged epochs are compared against its single fixed discovery product. A fresh scan of all 72 native header polynomials selects only order 70, whose historical raw panel remains explicit. The ±3 Å window is disjoint in wavelength from completed C001–C008 bounded contexts, but original epoch/profile and raw evidence already exists and all seven observations are reused. These are dependent archival observations.

The discovery reference is **ADP.2023-03-23T01:02:04.831**, observed on 22 March 2023, with BERV **3.26509772194068 km/s**. The barycentric center is **6802.02 Å** and the wavelength-specific fixed topocentric center is **6801.945918689643 Å**. The numeric anchor of C008 is not reused.

`independent_math.py` implements scalar interpolation using binary search, a signed pooled-flank median, first-difference MAD, common-support Pearson correlation and normalized RMS. It imports no production code. The 601-point grid has 51 core points and 550 surrounding points, with minimum common support of 41 and 440.

`audit_prospective.py` verifies singleton identity, fixed geometry, all 72 native header polynomials, source bindings, unchanged estimators and historical mappings. Synthetic fixtures exercise gaps, nonfinite flux, missing flanks, nonpositive references, zero variance, frame transforms and exact support boundaries. Analytic flux on header-derived order 70 coordinates checks complete geometric coverage; 19/20 finite-flank fixtures check the separate finite-count gate. Only this synthetic harness imports production functions as test subjects. It opens no observational arrays.

Order 70 geometrically covers the complete fixed ±3 Å window and both flanks in both frames. Actual finite-flux support, reference sign and noise remain unknown before release. Historical global, local, baseline and later five-window mapping flags are all true and retained as distinct earlier diagnostics.

The historical review chain remains explicit: primary A and secondary A were provisional artifact assessments of a compact slanted concentration; root adopted **U**, retaining a possible artifact/spectral blend. Supported mapping and descriptive shape statistics cannot silently replace the adopted disposition. The prospective and actual audits check that exact A/A/U provenance and its unresolved qualification.

After root release and production completion, `audit_actual.py --authorized-after-root-run` reopens exact sources and reconstructs eight bounded source windows, all 16 profiles and all 32 comparisons. It verifies the historical raw copy exactly and retains four labelled identical-product self comparisons. The actual reconstruction imports no production functions. Reports are one-shot outputs; failures are retained rather than replaced by an adjusted analysis.

These checks verify arithmetic and lineage consistency. They do not calibrate uncertainties, identify physical lines or origins, add observing time, alter the U label or turn reused observations into independent evidence.
