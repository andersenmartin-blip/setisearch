# LS7T: native housekeeping exposes a gain-input mismatch

15 September 2026. Same public CHEOPS visit `CH_PR300024_TG000301_V0300`,
OBSID 1015522. Continues the [LS7S audit](LS7S_CALIBRATION_FINDINGS.md).

**The actual PIPE input is now known:** the pinned reader uses a separate
CCD-voltage field in the temperature term. Running that unchanged function
on the native instrument table gives a median gain **0.57027% below** the
temperature-centered diagnostic. This is different from LS7S's explicitly
conditional 8.129% comparison, which inserted temperature into the expression.
Neither result establishes a calibrated source signal.

The audit also removes an unnecessary requirement: the missing individual
GAIN_0/BIAS_0/BIAS values describe onboard nonlinearity conversion, while both
raw products explicitly have that operation disabled. Their NaNs alone do
not prevent an offline calibration. Native readiness remains **NOT_READY**
because other physical inputs and conventions are still unresolved.

## Actual instrument input, without opening science pixels

The [scope](LS7T_SCOPE.md) was written before acquiring the already inventoried
SCI_RAW_HkExtended product. HkDefault is not the input expected by the pinned
PIPE gain path and was not acquired. Exact HTTP 206 ranges retained **165,480
bytes** of headers and instrument telemetry from a 167,040-byte FITS object;
the 1,560 trailing padding bytes were not transferred. All object identities,
range lengths and reconstructed table checksums pass.

There are **1,140 rows**, roughly 20 seconds apart, covering
2020-03-09 04:54:45.961561–11:14:27.401137 UTC. UTC strings and MJD in TT agree
within **0.315 microseconds**. No interpolation onto the exposure sequence
was performed, and no photometric field or science image was read.

| Native field | Observed range | Interpretation supported by the source schema |
|---|---:|---|
| TEMP_FEE_CCD | −40.008106 to −39.995396 | Separate CCD-temperature quantity |
| VOLT_FEE_CCD | +34.813713 to +34.815159 | Separate CCD-voltage quantity, used by the pinned PIPE reader |
| VOLT_FEE_VSS | 8.800056–8.800168 | VSS input |
| VOLT_FEE_VOD | 30.800354–30.800928 | VOD input |
| VOLT_FEE_VRD | 17.800793–17.800850 | VRD input |
| VOLT_FEE_VOG | 3.053650–3.053692 | VOG input |

The HkExtended table itself omits TUNIT on these six fields. The temperature
and voltage interpretation follows the mission schemas and the independently
unit-labelled CE/HK fields, not a claim that missing native unit cards exist.
[HkExtended schema](https://github.com/davefutyan/common_sw/blob/1e45b3be84edd18a60e9a0ea8ef65444dfa2a254/fits_data_model/resources/SCI_RAW_HkExtended.fsd),
[image HK units](https://github.com/davefutyan/common_sw/blob/1e45b3be84edd18a60e9a0ea8ef65444dfa2a254/fits_data_model/resources/ColumnHk.ifsd).

## The source disagreement is explicit

The verified V0109 reference has nominal gain 0.5111 ADU/electron and
TEMP_OFF = −40 °C. CHEOPSim reads that signed reference temperature and
subtracts it from the physical CCD temperature after converting Kelvin to
Celsius. Its voltage offsets agree with the centered LS7S algebra.
[Reference initialization](https://github.com/davefutyan/CHEOPSim/blob/d5bfcfdae596ae1b85576dced7d55baecbc7da4d/data/src/Data.cxx),
[gain implementation](https://github.com/davefutyan/CHEOPSim/blob/d5bfcfdae596ae1b85576dced7d55baecbc7da4d/detector/src/BiasGenerator.cxx).

In contrast, common_sw's gain schema writes a temperature-plus-offset term
while describing TEMP_OFF as the nominal signed CCD temperature. This is a
real disagreement between the inspected primary sources. It is not resolved
by selecting whichever calculation produces a desirable residual.
[Gain schema](https://github.com/davefutyan/common_sw/blob/1e45b3be84edd18a60e9a0ea8ef65444dfa2a254/fits_data_model/resources/REF_APP_GainCorrection.fsd).

The [pinned PIPE function](results_ls7s_calibration/sources/pipe_read.py)
reads VOLT_FEE_CCD and adds TEMP_OFF. LS7T executes only this reviewed,
unchanged function, using its real input columns. It does not initialize
PIPE, import its package, fit a PSF, load a pickle or perform an extraction.

| Diagnostic on the same 1,140 rows | Gain range, electrons/ADU | Full-visit span |
|---|---:|---:|
| Physical temperature minus signed offset | 1.956586526–1.956638408 | 26.5166 ppm |
| Physical temperature plus signed offset | 1.797538510–1.797582300 | 24.3610 ppm |
| Unchanged PIPE, native voltage plus offset | 1.945430235–1.945473157 | 22.0632 ppm |

The native PIPE/centered ratio differs by **−0.570782% to −0.569364%**, with
median −0.570272%. Removing that ratio's median leaves at most **9.1334 ppm**.
This is a gain-convention sensitivity, not observed stellar variability or
measured pulse attenuation. The older 8.129% value remains correct for its
different, conditional input substitution and is not the actual PIPE result.

Float32 input arithmetic in the unchanged reader is accounted for separately.
Using the same voltage expression in float64 changes the median-normalized
ratio by at most **0.03148 ppm**. It does not explain the quantity/sign issues.
The run uses NumPy 2.5.3 and Astropy 8.0.1; it is not a reproduction of the
mission's historical software environment or a claim about every PIPE release.

## What the metadata can and cannot require

The individual GAIN_0, BIAS_0 and BIAS fields are specifically the conversions
around **onboard nonlinearity correction**. Both native image headers have
NLIN_COR=false and ROUNDING=0. Therefore an inverse of that disabled onboard
operation is not an input requirement justified by these headers. The NaNs
remain missing values; they are not assigned zero or a nominal constant.
[Individual-exposure field definitions](https://github.com/davefutyan/common_sw/blob/1e45b3be84edd18a60e9a0ea8ef65444dfa2a254/fits_data_model/resources/SCI_RAW_UnstackedImageMetadata.fsd),
[raw product schema](https://github.com/davefutyan/common_sw/blob/1e45b3be84edd18a60e9a0ea8ef65444dfa2a254/fits_data_model/resources/SCI_RAW_SubArray.fsd).

Offline nonlinear correction is still required. The logged LUT100 schema
maps **uncorrected electrons to corrected electrons**, not raw summed ADU.
The small PIPE nonlin.txt is still not a substitute for the exact V0104 LUT.
[LUT100 schema](https://github.com/davefutyan/common_sw/blob/1e45b3be84edd18a60e9a0ea8ef65444dfa2a254/fits_data_model/resources/REF_APP_CCDLinearisationLUT100.fsd).

For a simple sum of n independent readouts with constant bias b, read noise r
in ADU and gain g in electrons/ADU, the summed bias is n b and read-noise
variance is n (g r)^2. For their mean, the variance is (g r)^2/n. Flat-field
division and nonlinear derivatives must subsequently propagate uncertainty;
shared bias/reference uncertainty can introduce covariance. These are
conditional mathematical identities, not an adoption of the native gcoadd
meaning or the CAL BIAS/RON units.

CHEOPSim's inspected writer implements coadd and mean; it does not establish
the separate native gcoadd contract. The CAL metadata schema supplies no
BIAS/RON units or stacking convention. The existing constant values cannot be
promoted to per-readout ADU simply from their magnitudes.
[Writer](https://github.com/davefutyan/CHEOPSim/blob/d5bfcfdae596ae1b85576dced7d55baecbc7da4d/simulator/src/ImageWriter.cxx),
[CAL schema](https://github.com/davefutyan/common_sw/blob/1e45b3be84edd18a60e9a0ea8ef65444dfa2a254/fits_data_model/resources/SCI_CAL_ImageMetadata.fsd).

## Verification and next decision

The raw-byte/struct and Astropy decoders agree for **9,120 selected field
values**. Four separate scalar evaluations check **4,560 gain values**,
including float32 intermediate arithmetic, with maximum absolute discrepancy
**4.45 × 10⁻¹⁶ electrons/ADU**. This is a second arithmetic path in this
project, not independent external review. Fourteen inspected source files
have verified pinned Git identities and SHA-256 records; their unlicensed
source bodies are not republished.

The [remaining contract](results_ls7t_contract/calibration_contract.json)
records which conditions are established and which remain open. Exact mission
reference contents, early-visit dark/bad-map applicability, gcoadd and the
gain-sign reconciliation still precede a prospective native study. The
previously policy-blocked reference-bundle action was neither repeated nor
bypassed. Its access limitation remains.

**No science images, native residual trials, pulse recoveries, candidates or
additional qualified coverage are added.** Continue from
[LS7T_CONTINUATION.md](LS7T_CONTINUATION.md); do not repeat the old censuses.
