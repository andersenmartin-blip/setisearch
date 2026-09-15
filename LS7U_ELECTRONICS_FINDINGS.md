# LS7U: direct CHEOPS electronic-reference measurements

Completed 15 September 2026 for the retained visit
`CH_PR300024_TG000301_V0300`, OBSID 1015522, 55 Cnc, observed 9 March 2020.
Continues [LS7T](LS7T_CALIBRATION_CONTRACT.md) without changing the visit or
opening its target-image planes.

**The four-column virtual prescan measures a bias of 562.089864 ADU per
readout and an effective read noise of 7.118046 ADU per readout.** This supplies
direct electronics evidence where LS7T had only recorded calibration numbers.
A separately specified check of the actual reference margin used by PIPE
does **not** reproduce those CAL numbers. The physical input remains
**NOT_READY_FOR_TARGET_IMAGE_STUDY**.

## Input and the two analysis scopes

The [primary protocol](LS7U_PRESCAN_PROTOCOL.md) was written before acquiring
the virtual prescan. It fixes HDU 7, `SCI_RAW_OverscanLeft`, four virtual
columns in each of 432 frames, with no clipping. The published protocol
identity records the local pre-acquisition specification; it is not an earlier
public preregistration commit.

The mission DRP paper describes four prescan columns with no photon or dark
current contribution, eight separate blank columns, and a bias/noise scaling
by the number of coadded readouts. It also distinguishes scalar offset from
the spatial bias correction. This motivates the prescan measurement but does
not establish the exact implementation of DRP 14.1.2.
[Hoyer et al., sections 2 and 4.2](https://arxiv.org/abs/1909.08363).

After the primary bias disagreed with CAL beyond its descriptive sampling
spread, the [supplement](LS7U_BLANK_SUPPLEMENT.md) fixed a separate read of
HDU 2, `SCI_RAW_BlankLeft`. The pinned PIPE reader selects that eight-column
extension by position. Its input selection was therefore checked as an
**exploratory follow-up**, specified before the blank values were acquired.
It does not replace the primary estimator or its result.

| Retained electronic extension | Array shape | Header bytes | Array bytes |
|---|---:|---:|---:|
| Primary: HDU 7, OverscanLeft | 432 × 200 × 4 | 8,640 | 1,382,400 |
| Supplement: HDU 2, BlankLeft | 432 × 200 × 8 | 8,640 | 2,764,800 |
| Total | 1,036,800 float32 values | 17,280 | 4,147,200 |

The new transfer is exactly **4,164,480 bytes**, including the re-read
headers. These are electronic reference **image-array bytes**, not metadata
and not the target image. Both extensions are unscaled float32 ADU with
`MRG_PROC=image`, `STACKING=coadd`, `NEXP=14`, `ROUNDING=0` and
`NLIN_COR=false`. The original object ETag, total size 90,938,880 bytes,
product identity, complete headers and both FITS checksums agree with LS7R.
All requests returned the exact bounded HTTP 206 ranges.

## Primary result and what the CAL comparison establishes

For each frame, bias is median/n and effective noise is population standard
deviation/sqrt(n), with n=14. The visit bias is the mean of the frame biases;
the visit noise is the RMS of the frame noise values. No frame or value is
discarded. The read-noise scaling assumes independent coadded readouts;
individual unstacked reference readouts are not available to test that premise.

| Quantity | Primary result, ADU/readout | Descriptive 0.5–99.5% block interval |
|---|---:|---:|
| Bias | 562.089864418 | 562.077708678–562.101262067 |
| Effective read noise | 7.118045642 | 7.089262047–7.149363589 |

The fixed 4,096-draw bootstrap uses 29 blocks of at most 16 frames, split at
the four known gaps. The five segments contain 31, 116, 119, 119 and 47
frames. These intervals describe within-visit sampling stability, not total
instrument-calibration uncertainty.

Alternative summaries are consistent in scale: mean of means gives a bias
of **562.089094329**; the mean normal-MAD noise is **7.108968692**; row-difference
noise is **7.097057174** ADU/readout. The four column mean biases range from
561.952455357 to 562.210910218. Full frame values and lag-one row diagnostics
are retained, including the highest-noise frame; no spatial structure is
fitted away.

The saved CAL/COR fields have BIAS=563.429992676 and RON=7.130000114, without
native column-unit cards. Under the explicit **per-readout ADU hypothesis**,
CAL is 0.238419% higher in bias and 0.167946% higher in noise. Both satisfy
the predeclared 1% numerical-agreement label. However, the **1.340128258 ADU
bias difference lies well outside the descriptive interval**; the bias is
not reproduced. The RON number lies within that interval.

The summed-ADU hypothesis predicts bias 7,869.258102 and noise 26.633288.
The three previously saved LS7T gain interpretations predict electron values
about 1,010–1,100 for bias and 12.795–13.927 for noise. Those hypotheses all
fail the same 1% comparison. This is evidence for the numerical scale of
the CAL fields, not documentation of their semantics or selection of a gain.
Every ratio is in [summary.json](results_ls7u_prescan/summary.json).

## What the original PIPE function returns

The unchanged `bias_ron_adu` and `sigma_clip` functions are loaded from
verified source at PIPE commit `da15a87348e2657eac8dd08623ac258e6ac59df8`.
Only those function ASTs execute; there is no complete PIPE extraction.
Their FITS input is a disclosed surrogate: a primary HDU, an empty HDU 1
carrying the actual native NEXP=14, and the original blank header/body at
HDU 2. No target-image data are needed by these two functions.
[Original reader](https://github.com/alphapsa/PIPE/blob/da15a87348e2657eac8dd08623ac258e6ac59df8/pipe/read.py),
[original clipping routine](https://github.com/alphapsa/PIPE/blob/da15a87348e2657eac8dd08623ac258e6ac59df8/pipe/pipe_statistics.py).

The routine globally clips at three standard deviations from the median for
ten iterations, allowing re-entry each time. It retains **685,916/691,200
values**, removing 5,284 (0.764468%). Clipping is confined to the electronic
reference diagnostic and is never applied to source flux.

| Reference diagnostic | Bias, ADU/readout | Effective noise, ADU/readout |
|---|---:|---:|
| Primary virtual prescan, fixed frame estimator | 562.089864418 | 7.118045642 |
| Blank margin, original PIPE function with gain=1 | 562.071428571 | 7.024590259 |
| Blank margin, global summary before clipping | 562.071428571 | 8.516313078 |

CAL exceeds the PIPE blank result by **1.358564104 ADU** in bias and
**0.105409855 ADU** in noise. CAL/PIPE is 1.002417067 for bias and
1.015005837 for noise: the noise **fails** the unchanged 1% agreement label.
Changing from the primary margin to PIPE's actual input does not explain
the CAL bias difference. The reduction in blank-margin dispersion after
clipping is explicit; it is not an adopted single-exposure noise model.

Running the same original function with the three LS7T median gains leaves
the clipping mask identical and gives the following **conditional** results:

| LS7T gain interpretation | Gain, electrons/ADU | Bias, electrons/readout | Effective noise, electrons/readout |
|---|---:|---:|---:|
| Centered physical temperature | 1.956626695 | 1,099.763961851 | 13.744500826 |
| Schema plus-temperature diagnostic | 1.797572414 | 1,010.364094635 | 12.627209669 |
| Pinned PIPE with actual native HK | 1.945468928 | 1,093.492499795 | 13.666122084 |

None is adopted as the science calibration. The LS7T field-mapping and
temperature-sign findings are unchanged. Supplement outputs, clipping counts
at every iteration and all 432 frame summaries are retained in
[blank_reference](results_ls7u_prescan/blank_reference).

## Additional source-contract evidence

The pinned common_sw `ValidRefFile` selects using actual validity headers
and revision metadata and requires the requested UTC inside a validity
interval. It supplies no demonstrated nearest-future fallback. Thus this
source does not explain how a dark/bad map whose archived start is 8.3126
days after this visit would apply. The actual reference headers and DRP path
are still uninspected; this is **not** a finding that the mission calibration
was invalid.
[Pinned validity selector](https://github.com/davefutyan/common_sw/blob/1e45b3be84edd18a60e9a0ea8ef65444dfa2a254/utilities/include/ValidRefFile.hxx).

The in-flight performance paper describes DRP 13/14 changes and dark-map
correction in version 14, which makes version-specific provenance relevant.
It does not deliver this visit's exact reference files or resolve their
early-visit selection here. No request to mission staff was sent.
[Fortier et al., section 2.3](https://arxiv.org/abs/2406.01716).

The simulator's separate default reference archive was inspected only as
release metadata. Its exact requested-version membership is unestablished;
it was not acquired or treated as a substitute for the blocked mission
reference-bundle action. No retry or workaround of that action is part of LS7U.

## Verification and decision

Every **1,036,800 electronic value** agrees between Astropy and independent
struct decoding. Scalar arithmetic checks 1,296 primary frame statistics.
For the supplement, every clipping mask agrees after each of ten iterations:
**6,912,000 Boolean comparisons**, with zero discrepancy in the final scalar
bias and noise. Source Git identities and native extension checksums pass.
Clean offline reconstruction reproduces both summary JSON files and both
compressed frame tables byte-for-byte, with zero network transfer and
unchanged acquisition manifests.
[Verification record](results_ls7u_prescan/verification.json).

The [updated physical contract](results_ls7u_prescan/calibration_contract.json)
now includes verified electronic-reference inputs, a measured ADU bias/noise
scale and a tested PIPE margin mapping. It still requires the gain convention,
native imagette gcoadd/offline nonlinearity operator, exact spatial calibration
contents and dark/bad-map applicability. Neither measured margin supplies a
science-pixel flat, spatial bias, dark map or PSF calibration.

**Zero target-image bytes, source residual trials, pulse recoveries, new
candidates or qualified observing seconds are added.** The unused TESS/M43
data remain closed. Next finish the missing physical-input package before
one prospective protected calibration, positive-pulse, nuisance and native
prediction study. Reuse these completed measurements instead of repeating
the census or adjusting an estimator to match CAL.
[Continuation](LS7U_CONTINUATION.md), [reproduction](results_ls7u_prescan/README.md).
