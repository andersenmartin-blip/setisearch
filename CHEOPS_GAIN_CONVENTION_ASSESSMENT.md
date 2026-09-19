# CHEOPS gain-reference convention assessment — 19 September 2026

Operational source reconciliation after LS7V. This assessment uses the already
verified GainCorrection V0109 file and public source/schema revisions. It does
not open target-image pixels, adopt a science calibration, rerun a native
signal test or add observing coverage.

## Exact retained reference

The retained reference is
`CH_TU2020-02-18T06-15-13_REF_APP_GainCorrection_V0109.fits`,
SHA-256 `8e5f363943dfd1165406ec553cbcbfeb7ee7cbacccb03c72ae1efc8e451a9918`.
Its verified table header records:

- `EXT_VER=12.1.5`
- `TEMP_OFF=-40.0 degC`
- `GAIN_NOM=0.5111`
- `RO_HW=main`
- validity 2020-02-18 through 2050-01-01.

This reference is therefore valid across the retained 9 March 2020 visit.

## Formal common_sw data-model semantics

The public CHEOPS common-software repository
`davefutyan/common_sw`, commit
`1e45b3be84edd18a60e9a0ea8ef65444dfa2a254`, contains
`fits_data_model/resources/REF_APP_GainCorrection.fsd`.
That schema is also version **12.1.5**, matching the retained FITS extension.

The schema explicitly defines the formula result as **system gain in ADU/e-**.
It specifies the five input quantities as the four FEE voltages plus
`HK_TEMP_FEE_CCD`; the temperature term is written as

`(HK_TEMP_FEE_CCD + TEMP_offset) ** exp_TEMP`.

The same schema labels `TEMP_OFF` as the nominal CCD temperature in degC.
The common data model for `SCI_RAW_ImageMetadata` independently defines
`HK_TEMP_FEE_CCD` as the CCD/FPA temperature in degC. Thus the formal
reference structure does not identify `VOLT_FEE_CCD` as the temperature
argument.

The public LUT100/LUT230 structures also state that their input/output values
are uncorrected and non-linearity-corrected **numbers of electrons**. This
confirms the electron-domain meaning of the LUT product family; it does not
by itself establish when a stacked `gcoadd` sample is converted to/from that
domain by DRP 14.0.1.

## CHEOPSim implementation

The public CHEOPSim source
`davefutyan/CHEOPSim`, commit
`d5bfcfdae596ae1b85576dced7d55baecbc7da4d` (package Makefile
`RELEASE_VERSION=r_13.6`), uses the same reference class.

`Data::setNominalVoltages` stores `TEMP_OFF` directly as the nominal
temperature. `BiasGenerator::process` then constructs the temperature
deviation as

`ccdTemperature - 273.15 - temp_nominal`.

With the retained signed `TEMP_OFF=-40 degC`, this centers a physical CCD
temperature near -40 degC around zero. CHEOPSim treats its gain variable in
ADU/e- and converts electrons to ADU by multiplying by that gain.

This differs in sign form from the literal common_sw schema expression.
CHEOPSim is simulator source, not evidence that DRP 14.0.1 uses the same
implementation.

## Pinned PIPE implementation

The public PIPE v1.1/current-main commit
`da15a87348e2657eac8dd08623ac258e6ac59df8` computes the reference
polynomial in `pipe/read.py::gain`, but assigns its temperature variable from
the HkExtended field `VOLT_FEE_CCD`, applies `+ TEMP_OFF`, and returns the
reciprocal as e-/ADU.

The retained native HkExtended table shows that `TEMP_FEE_CCD` and
`VOLT_FEE_CCD` are distinct finite quantities: the former is approximately
-40 while the latter is approximately +34.814. The common_sw reference
formula names the temperature quantity, not the latter voltage-named field.
This establishes a source/field mismatch; it does not establish the intent of
PIPE or an upstream software defect.

## Numerical relation to the executed DRP log

The already audited LS7T calculations give, on the retained native HK rows:

| Conditional interpretation | e-/ADU range |
|---|---:|
| Temperature centered at signed nominal | 1.9565865–1.9566384 |
| Literal schema `TEMP + TEMP_OFF` | 1.7975385–1.7975823 |
| Pinned PIPE native field path | 1.9454302–1.9454732 |

The executed DRP 14.0.1 log reports only **gain ~2.0 e-/ADU**. The centered
calculation is consistent with 2.0 under ordinary one-decimal rounding; the
literal schema-plus value would round to 1.8. This is useful diagnostic
evidence, but the log does not expose its formatter or exact computed value.
Therefore it is not sufficient to select the DRP formula prospectively.

The formal reference product itself is in ADU/e-, whereas the DRP log reports
the reciprocal-style unit e-/ADU. This is mutually coherent at the level of
unit inversion, but it still does not establish the exact DRP arithmetic or
the final CAL/COR pixel-unit transition.

## Revised decision

**REFERENCE_SEMANTICS_RESOLVED; DRP_GAIN_OPERATOR_NOT_YET_VERIFIED.**

We now know from a matching-version public schema that the GainCorrection
reference is defined in ADU/e- and formally depends on `HK_TEMP_FEE_CCD`.
We also know that two public implementations follow different temperature
paths. Do not choose one merely because its result is numerically closer to
the rounded DRP log.

The remaining gain task is narrower: obtain or identify the version-relevant
DRP 14.0.1 gain implementation, or authoritative documentation confirming
the temperature sign/centering and conversion order. The prepared technical
request should ask this exact implementation question if public source
recovery fails. Target-image evaluation remains blocked jointly by this
operator issue, exact `gcoadd`, and the missing flat/LUT/dark/bad-map
contents/applicability.
