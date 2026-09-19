# CHEOPS calibrated-imagette availability assessment — 19 September 2026

This assessment asks whether mission-delivered calibrated/corrected imagettes
can replace raw-imagette calibration for the retained 55 Cnc visit. It uses
only already published product inventories and public data-model schemas; no
new science pixels are opened.

## Data-model capability

The public CHEOPS data model at
`davefutyan/common_sw@1e45b3be84edd18a60e9a0ea8ef65444dfa2a254`
defines both:

- `SCI_CAL_Imagette`: L1 calibrated imagette cube;
- `SCI_COR_Imagette`: L1 calibrated and corrected imagette cube.

Both are double-precision image cubes with one metadata row per imagette. Their
metadata retain `NEXP`, time and detector offsets, and the image headers retain
the onboard `STACKING`, `ROUNDING` and `NLIN_COR` descriptors. Thus, in
principle, a mission-delivered high-cadence calibrated imagette stream exists
in the CHEOPS product model.

## Exact retained visit

The already frozen LS7R archive inventory for
`CH_PR300024_TG000301_V0300`, OBSID 1015522, contains:

- `SCI_RAW_Imagette` (L0.5);
- `SCI_RAW_SubArray` (L0.5);
- `SCI_CAL_SubArray` (L1);
- `SCI_COR_SubArray` (L1);
- L2 `SCI_COR_Lightcurve` products and auxiliary products.

It contains **no `SCI_CAL_Imagette` and no `SCI_COR_Imagette` row**.
The independent saved DACE product listing likewise contains the raw imagette,
CAL/COR subarrays and L2 light curves but no CAL/COR imagette product.

## Decision

**CAL_COR_IMAGETTE_ROUTE_UNAVAILABLE_FOR_RETAINED_VISIT.**

The data model proves that calibrated/corrected imagette products are valid
CHEOPS product types, but they are not exposed in the already frozen public
product inventory for this exact visit/revision. They cannot be assumed to
exist or substituted by name.

Accordingly:

1. the high-cadence raw-imagette route still requires the unresolved onboard
   `gcoadd` and physical calibration contract;
2. the mission-delivered calibrated route for this visit remains the
   30.8-second CAL/COR subarray plus L2 light-curve route already used by
   LS7X/LS7Y/LS7Z;
3. do not request or fabricate a CAL/COR imagette URL from the schema alone.

No new archive bytes, candidate decisions or observing coverage are added.
