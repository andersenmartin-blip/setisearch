# CHEOPS gcoadd structural constraints — 19 September 2026

This note combines version-relevant public data-structure semantics with the
exact-visit grouping result. It narrows the onboard `gcoadd` contract without
opening any target-image pixel values.

Pinned public schema source:
`davefutyan/common_sw@1e45b3be84edd18a60e9a0ea8ef65444dfa2a254`.

## Raw imagette representation

The public `SCI_RAW_Imagette.fsd` history records a 29 May 2018 schema change
from `uint16` pixels to **`uint32` “to be able to store stacked imagettes”**.
The current schema imports the ADU unit keyword and describes the L0.5 pixels as
the values received from the instrument, with no ground processing of the raw
pixel data.

This representation is consistent with a stack whose dynamic range can exceed
one constituent 16-bit exposure. It is strong structural evidence for an
additive/sum-like product, but by itself does not define `gcoadd` arithmetic.

## Visit-specific processing flags

The same raw imagette/subarray schemas define:

- `ROUNDING`: number of bits rounded off;
- `NLIN_COR`: onboard nonlinearity correction;
- `STACKING`: onboard stacking mode.

For the retained 9 March 2020 visit:

- imagette: `NEXP=2`, `STACKING=gcoadd`, `ROUNDING=0`,
  `NLIN_COR=false`;
- subarray: `NEXP=14`, `STACKING=coadd`, `ROUNDING=0`,
  `NLIN_COR=false`.

Therefore **zero separate rounding bits are removed** and **onboard
nonlinearity correction is disabled** for both retained image products. This
is also consistent with the OBDP chain, where preprocessing precedes stacking
and rounding is a later separately configured stage.

## Unstacked metadata semantics

`SCI_RAW_UnstackedImageMetadata.fsd` explicitly states that all constituent
images stacked into one image share the same `CE_COUNTER`. Its
`GAIN_0/BIAS_0/BIAS` fields are specifically tied to conversion around
**onboard NLC**. Since `NLIN_COR=false`, their missing values do not define a
missing operation that must be inverted.

## Combined constraint on gcoadd

The evidence now jointly establishes:

1. the exact visit groups **two** constituent 2.2-second readouts per imagette;
2. the delivered raw imagette storage is 32-bit unsigned ADU and the schema was
   widened explicitly to support stacked imagettes;
3. no separate onboard bit-rounding step is active (`ROUNDING=0`);
4. onboard NLC is disabled;
5. the public PIPE raw-imagette path scales bias with `NEXP` and evaluates
   nonlinearity on a per-exposure level after division by `NEXP`.

Items 2 and 5 make a simple mean-normalized raw representation difficult to
reconcile with the public ecosystem and favor an additive/sum-like
interpretation. They do **not** prove the exact flight implementation.

Still unresolved before a formal `gcoadd` verification:

- whether the two values are added directly or through a generalized accumulator;
- saturation/clipping policy;
- accumulator width and overflow behavior;
- any special invalid-pixel handling;
- whether a normalization other than the separately disabled rounding stage is
  applied internally.

Do not substitute these constraints for RD-11 or flight-source code. Current
decision remains **NOT_READY_FOR_TARGET_IMAGE_STUDY**.
