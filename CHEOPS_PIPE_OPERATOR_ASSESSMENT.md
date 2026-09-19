# CHEOPS PIPE public operator assessment — 19 September 2026

This is a public-source implementation assessment supporting the prospective
CHEOPS native-image study. It does not open target-image pixels, adopt PIPE as
the detector, or establish the onboard `gcoadd` definition.

Pinned public source:
`alphapsa/PIPE@da15a87348e2657eac8dd08623ac258e6ac59df8`.

## Raw imagette/subarray calibration sequence implemented by PIPE

The pinned `PsfPhot.read_data()` initializes gain/bias, then reads raw
subarrays and raw imagettes. For both raw cubes the explicit calibration path
in `pipe/psf_phot.py` is:

1. obtain a time-dependent gain in **electrons/ADU**;
2. multiply the raw cube by that gain;
3. subtract the bias multiplied by `NEXP`;
4. divide by the temperature-interpolated flat, if enabled;
5. apply the optional CTI multiplicative correction;
6. apply the optional non-linearity correction.

For the non-linearity lookup, PIPE evaluates the correction at
`calibrated_signal / gain / NEXP`, i.e. a per-constituent-exposure ADU-like
argument after the preceding operations, then multiplies the current cube by
the returned correction factor. The same pattern is used for subarrays and
imagettes.

This is a concrete public operator. It is **not** evidence that DRP 14.0.1 uses
the identical implementation or order.

## Flat-field selection

`pipe/read.py::flatfield()` reads the reference temperature table, keeps rows
whose `DATA_TYPE` is `FLAT FIELD`, brackets the requested stellar effective
temperature and linearly interpolates between the two adjacent flat planes.
The detector crop is selected from the supplied offset and shape.

This gives an executable interpretation for the retained target's
`T_EFF=5196` and geometry once the exact flat V0104 content is available.
It does not prove that the DRP 14.0.1 selection/interpolation code is identical.

## Dark and bad-map selection

The pinned public PIPE implementation provides explicit reference-selection
rules:

- dark references are discovered by filenames containing
  `REF_APP_DarkFrame`;
- each reference time is read from extension-1 header `V_STRT_U`;
- the two closest times bracketing the science MJD are selected and their dark
  images are linearly interpolated in time;
- outside the available reference-time range, the nearest endpoint is used
  twice, so no extrapolation is performed;
- bad-pixel maps are discovered by `REF_APP_BadPixelMap` and the map with the
  nearest `V_STRT_U` is selected.

The dark uncertainty is propagated quadratically under the interpolation. PIPE
then crops the detector region and scales the dark to exposure time. These rules
are useful as a fully specified **PIPE method**, but do not establish the
version-specific DRP 14.0.1 reference-selection semantics.

## Gain caveat retained

`pipe/read.py::gain()` declares an e/ADU result, but the pinned implementation
assigns `data['VOLT_FEE_CCD']` to its temperature variable and uses
`temp_ccd + TEMP_OFF`. That is the already documented field/sign discrepancy
relative to the matching CHEOPS gain schema and CHEOPSim. This assessment does
not adopt PIPE's gain convention for the prospective study.

## Why this still does not resolve gcoadd

A repository search of the pinned PIPE source finds no use of the FITS
`STACKING` keyword. The raw imagette path uses the header `NEXP` and later
normalizes the non-linearity argument by `NEXP`, but does not distinguish
`gcoadd` from another onboard stacking mode.

Therefore PIPE's successful handling of CHEOPS imagettes cannot by itself prove
that a raw `gcoadd` pixel is a simple sum, mean, weighted sum, clipped sum, or
another generalized operator. Using PIPE as evidence for the onboard operator
would be circular.

## Revised use in SETIsearch

PIPE now provides a concrete public fallback definition for several **ground**
steps: flat temperature interpolation, dark time interpolation, nearest
bad-pixel map selection and a raw-cube calibration sequence. These may be used
only if the prospective protocol explicitly chooses PIPE semantics and records
that choice before target-image evaluation.

The blocking requirement is narrower but remains real:

1. establish the onboard `gcoadd` numerical contract for the retained
   `NEXP=2` imagettes;
2. establish/adopt a physically justified gain convention;
3. receive and hash the exact LUT/flat/dark/bad reference contents;
4. choose either version-relevant DRP semantics or an explicitly declared
   independent PIPE-based reference-selection/calibration path before freeze.

Current decision: **NOT_READY_FOR_TARGET_IMAGE_STUDY**.
