# LS7W auxiliary calibration-source assessment — 19 September 2026

Operational continuation after LS7V and the bounded public-source follow-up.
This file records what can be learned from public CHEOPS schemas, PIPE and DRP
documentation without opening target-image pixels. It is **not** an adoption
of PIPE as the mission DRP and not a replacement for missing DRP 14.0.1
implementation details.

## Public schema constraints

The CHEOPS common software data model at commit
`1e45b3be84edd18a60e9a0ea8ef65444dfa2a254` provides version-relevant
structure definitions:

- `REF_APP_FlatFieldTeff` version 12.1.5 is a 1024 x 1024 x Teff float cube.
  The schema states that flat fields are normalized to their average value and
  that one flat-field pixel corresponds to one CCD pixel. The associated
  metadata table contains `DATA_TYPE`, `T_EFF` in K and `STATUS`.
- `REF_APP_DarkFrame` version 12.1.5 contains two 1024 x 1024 planes:
  dark current and dark error. Its declared unit is e-/s. The schema states
  that bias has already been subtracted and non-linearity corrected.
- `REF_APP_BadPixelMap` version 12.1.5 is a 1024 x 1024 int16 map. Values
  are documented as -2 dead, -1 partially dead, 0 good, 1 hot, 2 saturated,
  3 telegraphic.
- `REF_APP_CCDLinearisationLUT100` version 12.1.5 maps uncorrected electrons
  to corrected electrons and carries the common UTC validity keywords.
- the shared `KeywordValidityUTC` definition establishes `V_STRT_U` and
  `V_STOP_U` as the UTC start and stop of validity.

These schemas resolve product meaning and units, but not which exact reference
instance DRP 14.0.1 selected for this early visit.

## What the pinned public PIPE implementation does

PIPE commit `da15a87348e2657eac8dd08623ac258e6ac59df8` is an independent
CHEOPS reduction/extraction implementation, not the official DRP.

Its `read.py` reference selectors use the reference header `V_STRT_U`:

- dark frames: choose the two closest bracketing validity-start times and
  linearly interpolate the dark and its error; outside the available time
  range the nearest frame is used twice;
- bad-pixel maps: choose the map whose `V_STRT_U` is nearest in time.

PIPE does not use `V_STOP_U` in those two routines. This is useful evidence
about one public analysis implementation only; it does **not** establish the
official DRP 14.0.1 selection rule.

PIPE's flat-field reader filters metadata rows to `DATA_TYPE='FLAT FIELD'`,
locates the target effective temperature between adjacent `T_EFF` rows and
linearly interpolates the corresponding detector planes. Detector subimages
are selected with Python half-open slices using the supplied full-array offset
and shape. For the retained subarray this public implementation would therefore
interpret `X_WINOFF=715, Y_WINOFF=181, 200 x 200` as the rectangle
x=[715,915), y=[181,381); this is an implementation observation, not yet an
authoritative DRP coordinate-contract claim.

For imagettes PIPE obtains the full-detector offset from the imagette metadata
(`X_OFF_FULL_ARRAY`, `Y_OFF_FULL_ARRAY`) and applies the same flat reader.
The retained visit's already audited full-array imagette offset is (790,256).

## PIPE calibration order is not a DRP proxy

The same pinned PIPE source makes the distinction important. For raw subarrays
and imagettes it:

1. multiplies raw ADU by its e-/ADU gain;
2. subtracts bias times NEXP;
3. divides by the interpolated flat;
4. optionally applies CTI correction;
5. applies its separate non-linearity correction, evaluating that correction
   with a per-exposure quantity obtained by dividing by gain and NEXP.

The official CHEOPS DRP architecture instead documents the high-level sequence
bias -> gain conversion to electrons -> linearisation -> dark -> flat. The
actual retained DRP 14.0.1 log likewise records its own executed path.

Therefore PIPE is valuable for independent geometry/reference semantics and
for designing checks, but its calibration order and its simplified reference
selection must not be substituted for DRP 14.0.1.

## Dark-current physics available from the official DRP paper

Hoyer et al. (2020), section 4.5, explicitly models dark accumulation with a
per-pixel time map depending on NEXP, exposure time and readout position.
The fixed dark frame is scaled in the dark-current correction and applied
after linearisation in electron units. This independently supports that the
dark reference is physically relevant and cannot be replaced by a constant
per-frame subtraction for this study.

The current visit log says the dark MAP correction was actually applied.
Consequently the exact dark-map contents and the version-specific selection
rule remain blocking even though the product's units and structure are now
well constrained.

## Revised dependency state

The following are now constrained well enough to pre-write invariant parts of
the prospective study:

- flat product geometry, normalization semantics and Teff metadata structure;
- dark product units and two-plane structure;
- bad-pixel class encoding;
- LUT electron-domain input/output semantics;
- UTC validity-key meaning;
- one independent public implementation's time-selection and detector slicing;
- official high-level DRP calibration order and dark-current time-map physics.

The following remain unresolved and must not be guessed:

- exact DRP 14.0.1 gain temperature/housekeeping adapter;
- exact onboard `gcoadd` arithmetic for NEXP=2 imagettes;
- exact contents/hashes of flat V0104, LUT100 V0104, dark V0201 and bad-map
  V0201;
- official DRP 14.0.1 reference selection/interpolation rule, especially for
  the early visit;
- any PSF reference required by the final protected estimator.

**Decision: AUXILIARY_CONSTRAINTS_ADVANCED; TARGET_IMAGE_STUDY_STILL_BLOCKED.**

No target-image bytes, photometric values, native trials, candidates or new
qualified coverage are introduced by this assessment.
