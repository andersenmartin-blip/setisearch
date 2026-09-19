# LS7Y independent-audit correction for centroid storage precision

The fourth LS7Y workflow again reproduced the unchanged frozen evaluator and
then stopped in the independent audit. The first mismatch was the three-row
mean CENTROID_X for cluster 0: the evaluator and audit differed by about
2e-5 pixel.

The L2 FITS schema declares LOCATION_X/Y and CENTROID_X/Y as `1E`, i.e.
big-endian binary32 values. The evaluator parses the FITS table with its native
binary32 dtype, so NumPy's mean reduction remains binary32. The first audit
parser decoded the same bytes correctly but immediately promoted the centroid
arrays to Python/NumPy float64 before the mean.

The audit parser is therefore corrected to retain binary32 for CENTROID_X/Y.
BJD remains binary64 as declared by its `1D` FITS column. No evaluator code,
pixel mask, candidate context, threshold, classification gate or scientific
output is changed. The correction is solely to reproduce the declared input
storage precision in the independent arithmetic.
