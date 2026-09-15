# LS7U: measure electronics from the virtual left prescan

Written 15 September 2026 before reading the margin values. Continues LS7T
commit `cce48a2b49ff5260b430291ac016ae805bc55dbe`. This executes the planned
option of deriving bias/read-noise evidence from properly scoped prescan data.
It does not open the target images or qualify a source detector.

## Fixed input and transfer

Keep CHEOPS visit `CH_PR300024_TG000301_V0300`, OBSID 1015522. LS7R has already
verified the raw subarray object's headers and geometry. Select **only HDU 7,
SCI_RAW_OverscanLeft**: 432 frames, 200 rows, 4 virtual columns, float32 ADU,
MRG_PROC=image, STACKING=coadd, NEXP=14, ROUNDING=0, NLIN_COR=false.

The selection follows Hoyer et al. 2019/2020 section 4.2 and figure 3's four
left prescan columns, together with the native header. SCI_RAW_BlankLeft is
a different eight-column extension at HDU 2; a positional `hdul[2]` access
must not be described as the four-column prescan on this native file.

One 8,640-byte header range begins at 86,803,200. The sole array range begins
at 86,811,840 and is exactly 1,382,400 bytes. Total transfer bound: **1,391,040
bytes**. Require HTTP 206, exact range/length and the original LS7R object
ETag, length and product identity. Compare the entire returned header with
the saved header before reading the array. Refuse any changed geometry,
object, heap, scaling, units, margin processing or ignored range. No full-file
fallback, additional margin, dark column or target-image read is allowed.

Use the documented public DACE visit-product route. This is distinct from
the previously URL-policy-blocked mission reference-bundle action, which must
not be retried or bypassed. Preserve exact range bytes losslessly compressed,
their uncompressed and compressed hashes, response provenance and FITS checksums.
Report these honestly as **virtual reference-array bytes**, not metadata.

## Declared arithmetic and comparisons

Decode every margin value independently with Astropy and struct. A checksum,
geometry, nonfinite-value or byte-identity failure stops the assessment; do not
drop frames or reinterpret missing data. No clipping or fitted reference map
is applied. Preserve all 432 frame results.

For each frame, compute the mean and median in summed ADU, divided by n=14
to estimate bias per readout. Compute population standard deviation and
1.482602218505602 times MAD, divided by sqrt(n), as alternative noise summaries
in ADU per readout. Also report row-adjacent difference standard deviation
divided by sqrt(2n), mean levels by column, and lag-one row covariance. These
diagnose spatial structure/correlation; do not silently call every dispersion
an independently measured single-exposure detector RON.

The primary visit summaries are the mean of frame medians/n and RMS of frame
population standard deviations/sqrt(n). Retain untrimmed means and robust
summaries alongside them. Quantify sampling stability with 4,096 fixed-seed
bootstrap draws of consecutive, at-most-16-frame blocks, split at the already
known >100-second time gaps. Resample blocks and weight by their frame counts.
The 0.5/99.5 percentiles are descriptive intervals, not mission-calibration
uncertainty budgets or independent-visit qualification.

Compare the saved CAL/COR BIAS=563.4299926757812 and RON=7.130000114440918
with the prescan summaries under explicitly labelled candidate units:
per-readout ADU, summed ADU (n for bias, sqrt(n) for noise), and electrons
using each already saved LS7T median diagnostic gain. Do not choose a gain
formula from the best match. A ratio within 1% is labelled numerical agreement;
it does not, by itself, document the CAL column's intended units or reproduce
the unpublished DRP algorithm. Show every candidate ratio, including failures.

## Decision and scope limits

The useful endpoint is direct electronic-offset/noise evidence and whether
the recorded CAL numbers are consistent with explicit unit/scaling hypotheses.
Use it to refine the physical input contract. Do not adopt a complete image
calibration, flat/bias spatial map, gcoadd definition or source uncertainty from
this margin-only result. A different prescan estimator needs a new stated reason;
do not tune it to reproduce CAL values. No pulse injection or target flux is read.

The exact mission reference contents, gain-sign reconciliation, native gcoadd
and early dark/bad-map applicability remain distinct requirements. The generic
common_sw validity selector has no demonstrated early-visit fallback; this does
not establish how the actual DRP chose its dark file. Preserve these distinctions.

Publish the protocol, lossless electronic ranges, code, full derived table,
verification and findings under the standing SETI authorization. Keep the
reserved TESS/M43 data closed and archive-staff contact unsent.
