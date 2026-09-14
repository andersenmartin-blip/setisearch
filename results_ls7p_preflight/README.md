# LS7P pre-acquisition verification

Seven analytic known-answer cases pass. The first calibration pass exposed the
inherited rejection of nonzero original rowShift/columnShift annotations.
Those unsupported cases are explicitly retained, before pixel acquisition.
The completed preflight has 216 case slots: 189 available calculations and
27 unavailable slots (three reference/convention pairs). The independent raw
FITS / SciPy reconstruction passes 924 numerical comparisons; its maximum
absolute difference is 2.9094504583326852e-12. No new reference pixel rows or
cosmic-ray amplitudes were read. This verifies calculation, not astrometry.
