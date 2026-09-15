# LS7S: CHEOPS calibration inputs and electronic metadata

15 September 2026. **The electronic-input audit is complete; native image
evaluation remains NOT_READY.** This continues the same 55 Cnc visit retained
in LS7R. It identifies specific calibration requirements before source-pulse
injections, without opening any science image or photometric value.

## What was established

The mission archive's reference query returned 792 records across the fifteen
requested reference families. Exact filename filtering found **14 of the 15
recorded versions**. The missing match is
`CH_TU2019-12-18T00-00-00_REF_APP_Aperture_V0300.fits`; absence in this query
does not establish absence everywhere. No different aperture version was
substituted. An aperture library need not be a direct input to a future PSF
fit, but reproducing DRP aperture photometry would require resolving it.

The dark and bad-pixel V0201 rows both start at **17 March 2020, 12:29:01 UTC**,
**8.3126 days after** the first saved exposure on 9 March. Their filenames
and archive dates are consistent; their FITS contents and early-visit
applicability are unverified. The saved processing log explicitly says that
DRP used this dark file. This evidence does **not** prove DRP used an invalid
calibration: an early-mission nearest-reference policy or another documented
rule may apply. It must be established before adopting the map.

The listed bias image is 102.1780 archive megabytes; the temperature-dependent
point-source flat is 1168.0200. They were deselected before a bounded download
of the twelve smaller matched references. That download did not complete:
the browser reported a URL-policy block after a transport error. No reference
bytes were retained from that operation, and the blocked archive action was
not retried through another route. This is an access limitation for this
session, not evidence that public archive delivery is generally unavailable.

One small reference was obtained from a distinct, verified software
distribution: the official **pipe-cheops 1.1 wheel on PyPI**. The 1,522,572-byte
wheel passes its published SHA-256; only the gain reference, nonlinearity text
and GPL licence were extracted, without installing or executing PIPE. The
**14,400-byte gain FITS file** matches upstream Git blob
`3bde861175310b797e53a9be506d9f2eab816a73` exactly. Its 21-row coefficient
table passes CHECKSUM and DATASUM, its UTC validity interval contains every
exposure, and its `main` readout-hardware value matches the raw subarray.
This verifies one of the fifteen reference files' contents.

## Actual electronic metadata

The saved exposure, imagette and subarray joins from LS7R are preserved.
Only explicitly selected electronic fields were added to the assessment.

| Input | Measured result | Consequence |
|---|---|---|
| Individual-exposure `GAIN_0`, `BIAS_0`, `BIAS` | All three are NaN in **all 6,048 rows**, or 18,144 missing entries | They cannot directly reconstruct the onboard conversion; NaN is not zero or nominal gain. |
| Four CE voltage fields and CCD temperature | All five are finite in all 6,048 rows | The electronic polynomial has available inputs, subject to its field/unit mapping. |
| CCD temperature | **−40.008698 to −39.991867 °C** | It is close to the gain reference's signed −40 °C offset. |
| Subarray timing script and digital offset | Script **6** and `PIX_DATA_OFFSET=256` in all 432 rows | The SEM digital offset is not automatically the measured bias. |
| CAL and COR metadata bias / RON | Constant **563.429993 / 7.130000**; both products agree exactly over 432 rows | These are recorded metadata values; their application and per-exposure scaling for raw imagettes remain to be established. |
| `STACKING` header | Imagettes **gcoadd**, subarrays **coadd** | Shared timing does not establish equivalent upstream calibration. |

The delivered subarrays contain groups of fourteen individual exposures;
the imagettes contain groups of two. No unstacked science images are present
in the metadata package. The constant CAL/COR numbers are not treated as
independent measurements on all 432 rows, and are not silently applied to
the imagettes. `PHOTOMETRY_1/2/3` remain excluded.

## Gain convention diagnostic

The gain reference has `GAIN_NOM=0.5111` and `TEMP_OFF=−40.0 °C`. The pinned
[PIPE reader](https://github.com/alphapsa/PIPE/blob/da15a87348e2657eac8dd08623ac258e6ac59df8/pipe/read.py)
uses a temperature-plus-offset expression and reads a differently named HK
temperature input (`VOLT_FEE_CCD`). The reference header describes an offset
for `HK_TEMP_FEE_CCD`. Blindly adapting that expression to the existing
degree-C metadata therefore needs checking.

We evaluate both algebraic conventions on the same 6,048 existing CE rows:

| Conditional interpretation | Temperature factor | Calculated gain range, electrons/ADU |
|---|---|---|
| Signed reference centering | `T − TEMP_OFF` | **1.956603536–1.956649248** |
| Literal pinned PIPE expression with the unverified field adapter | `T + TEMP_OFF` | **1.797552866–1.797591449** |

The second calculation is **8.12892–8.12909% lower** in absolute gain. After
removing the median ratio, its maximum relative variation is only
**1.0243 ppm**. This is mainly an absolute-scale difference in this diagnostic,
not evidence for an 8% time-variable astronomical signal or an 8% loss of
normalized pulse amplitude. The respective full-visit gain spans are
23.3634 and 21.4642 ppm.

**Neither formula is adopted as the physical calibration.** This is not a
PIPE reduction of the observation: the expected HK file was not provided,
and the adapter between differently named fields is unverified. It does not
establish an error in PIPE or DRP. It establishes why the temperature
mapping and offset convention cannot be copied without verification. The
reference coefficient uncertainties lack a covariance model here; no
calibrated uncertainty or sensitivity is inferred from this comparison.

The small packaged `nonlin.txt` has two interpolation points and is preserved
as provenance only. It is **not** the recorded
`REF_APP_CCDLinearisationLUT100_V0104` and was not applied.

## Audit and decision

The offline audit passes **87,696 scalar field comparisons**, including
missing-value equality, and **147 gain-coefficient comparisons** against
direct FITS byte decoding. A separate scalar polynomial evaluation agrees
on all **12,096 conditional gain values**, with maximum absolute difference
**6.67 × 10⁻¹⁶**. A known-answer case at the signed reference offsets returns
the nominal reciprocal gain. This is a second arithmetic path in the same
assessment, not an external review or an independent astronomical experiment.

**Decision: do not yet open native image pixels.** Only the gain reference's
contents are validated. The exact flat, LUT, bias/readout, dark/bad-pixel
applicability, PSF, coaddition mapping and instantaneous defect handling are
still needed. The numerical audit passes; the physical input contract is
incomplete. Consequently this stage has **zero native trials, zero pulse
recoveries, zero new candidates and zero added qualified observing coverage**.

The next step is a single combined calibration-resolution and pixel-response
study on this visit. The precise missing inputs and prospective experiment
requirements are in [LS7S_CONTINUATION.md](LS7S_CONTINUATION.md). The native
protocol has not been falsely labelled frozen or executed. Earlier TESS,
LS7Q and LS7R outcomes and LS7P's separate reconciliation stay unchanged.

[Evidence, exact sources and offline reproduction](results_ls7s_calibration/README.md).
[Scope and claim boundaries](LS7S_SCOPE.md).
