# LS8H — GJ 849 cluster-0 paired-image metadata scope

Status: **FROZEN BEFORE GJ 849 CAL/COR IMAGE ACCESS**.

LS8G produced one prospectively screened positive L2 cluster in
`CH_PR100018_TG032401_V0300`. The fixed representative is row **75**,
duration **1** row, score **23.4700798115**, with context rows **61:90**
(zero-based, stop-exclusive). The second selected GJ 849 visit has no signed
crossing and is not opened for image diagnosis.

This milestone is a bounded diagnostic follow-up of that already selected
excursion. It is not a new detector test and the L2 score is not a Gaussian
significance.

## Metadata-only first stage

Acquire headers and only the `SCI_CAL_ImageMetadata` and
`SCI_COR_ImageMetadata` tables from the exact V0300 CAL/COR subarray products
for `CH_PR100018_TG032401_V0300`. Skip every image array and smearing array
during this preflight. Require HTTP 206, exact ranges and stable ETag/object
identity.

Join each of L2 context rows 61–89 to exactly one CAL and one COR exposure by
native time metadata, requiring <=1 ms MJD/BJD agreement and exact UTC text.
Verify CAL/COR CE counter/integrity agreement, image dimensions, pixel type,
native offsets, BUNIT, PIPE version, NEXP/EXPTIME/TEXPTIME and the smearing-row
layout.

No image-plane index may be inferred from L2 row number alone.

## After metadata join

Only if all 29 context rows have unique CAL/COR joins, publish an exact machine
manifest containing the future CAL, COR and smearing byte ranges. Then freeze
the paired-image diagnostic before opening those payloads.

Reuse the already predeclared LS8D image semantics: same temporal sidebands and
guards, both coordinate conventions, fixed radii 25/35 and 30<r<=40 annulus,
CAL/COR/DELTA event maps, column-constant diagnostic, smearing regression and
brightness/displacement fits. The descriptive closure rules remain
CORRECTION_LINKED first, then SPATIALLY_STRUCTURED, otherwise
UNRESOLVED_WITHIN_FIXED_SCOPE.

Do not widen to another cluster, visit, aperture or raw imagette based on the
outcome.
