# LS7U supplement: identify the margin used by the pinned PIPE reader

Written after the primary four-column prescan result, but before acquiring
the eight-column blank-reference values. This is a separately scoped,
exploratory input-mapping check within LS7U. The original prescan protocol,
input restriction, estimator and results remain unchanged.

The primary bias is 562.089864 ADU per readout, whereas CAL records
563.429993. This difference is much larger than the primary bootstrap's
sampling spread. The already pinned PIPE bias_ron_adu routine reads HDU 2,
which the original native header identifies as SCI_RAW_BlankLeft, with eight
reference columns. It does not read the four-column SCI_RAW_OverscanLeft.
The purpose here is to check that concrete alternative input, not to tune the
primary estimator toward the recorded CAL number.

Acquire only the same raw subarray object's **HDU 2 SCI_RAW_BlankLeft**,
432 x 200 x 8 float32 values in ADU, MRG_PROC=image, STACKING=coadd, NEXP=14,
ROUNDING=0 and NLIN_COR=false. Its header starts at 69,134,400 and is 8,640
bytes; its electronic reference array starts at 69,143,040 and is 2,764,800
bytes. The supplemental limit is exactly **2,773,440 bytes**. Combined with
the primary, maximum new range transfer is **4,164,480 bytes**. No dark,
top/right margin, imagette, subarray target plane or photometry is authorized
by this supplement. The same ETag/length/header identity, HTTP 206 and FITS
checksum requirements apply. The blocked reference-bundle action is unchanged.

Verify all 691,200 values against struct decoding. Execute only the reviewed,
unchanged PIPE bias_ron_adu and its sigma_clip dependency from commit
da15a87348e2657eac8dd08623ac258e6ac59df8. Its fixed estimator globally clips
at three population-standard-deviations from the median for ten iterations,
then divides median by n and standard deviation by sqrt(n). Preserve selected
counts and independently reproduce them with scalar arithmetic. This is an
electronic reference diagnostic; never apply that clipping to source flux.

Use gain=1 to report the original-function result in ADU, and the three LS7T
median gains to demonstrate its electron conversion. The minimal FITS input
may contain an empty placeholder at HDU 1 carrying the actual NEXP=14 and the
original blank extension at HDU 2. Explicitly disclose that surrogate; it
contains no science pixels and is not a full native product or PIPE extraction.

Compare blank- and prescan-derived values with the unchanged CAL/COR numbers
and retain the original 1% descriptive agreement label. Never treat agreement
as exact DRP reproduction or a replacement for the spatial bias reference.
Show the residual bias offset and all gain-scaled results. Do not change the
chosen margin, clipping, gain or thresholds after reading the blank values.
