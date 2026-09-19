# LS7Y — CHEOPS L1 image-domain follow-up of the frozen LS7X screens

Frozen 19 September 2026 before any SCI_CAL/SCI_COR subarray science pixel
from the two LS7X candidate contexts is read.

LS7Y is a bounded diagnostic follow-up of the prospectively frozen LS7X
DEFAULT-aperture L2 pilot. It does not alter the LS7X threshold, durations,
sidebands, guards, aperture selection or clustering rule, and it does not
reconstruct the unavailable earlier local LS7W artifacts.

## Fixed parent result

LS7X evaluated exactly one mission-delivered L2 product for
`CH_PR300024_TG000301_V0300` (55 Cnc, OBSID 1015522):

- DEFAULT aperture radius: 25 pixels
- 432 L2 rows
- 826 eligible 1/2/3-cadence windows
- positive threshold: score >= 8.5
- negative control: score <= -8.5
- two positive clusters, zero negative controls

The fixed cluster representatives are:

| cluster | event rows | context rows | LS7X score |
|---:|---:|---:|---:|
| 0 | 66–68 | 52–82 inclusive | 10.27657667466243 |
| 1 | 185–187 | 171–201 inclusive | 9.118532025193854 |

The contexts are exactly the LS7X 12+12 sidebands, two-row guards and
three-row representative event. No neighboring row may be added after image
values are visible.

## Fixed products and byte boundary

Acquire only the corresponding frames from these public products:

- `CH_PR300024_TG000301_TU2020-03-09T04-59-05_SCI_CAL_SubArray_V0300.fits`
- `CH_PR300024_TG000301_TU2020-03-09T04-59-05_SCI_COR_SubArray_V0300.fits`

Both image cubes are fixed 432 x 200 x 200, FITS BITPIX=-64, with the image
array starting at byte 17,280. One frame is therefore exactly 320,000 bytes.
Read two contiguous 31-frame ranges per product:

- rows 52–82: 9,920,000 bytes
- rows 171–201: 9,920,000 bytes

Total subarray science transfer is exactly **39,680,000 bytes**. Require the
previously recorded LS7R object identities:

- SCI_CAL total 138,343,680 bytes; ETag
  `"1678907803.6927166-138343680-354560397"`
- SCI_COR total 139,812,480 bytes; ETag
  `"1678908364.0785742-139812480-383003041"`

Every request must return HTTP 206, the exact Content-Range, unchanged ETag,
exact Content-Disposition and exact byte count. Never fall back to a whole-file
download.

Also read only the corresponding 62 rows from the existing
`SCI_COR_SmearingRow` extension after verifying its header. Its array begins
at byte 138,424,320 and contains 432 x 200 float64 values. The two context
ranges contain 99,200 data bytes in total. No other image rows, imagettes,
apertures or visits are opened.

## Fixed coordinate conventions

The subarray headers give X_WINOFF=715 and Y_WINOFF=181. Because the archive
documentation available here does not independently fix the pixel-offset index
base, carry both conventions through every aperture result:

- C0: local center = (CENTROID_X - 715, CENTROID_Y - 181)
- C1: local center = C0 - (1,1)

For each convention, an aperture pixel has integer center coordinate
`(x,y)`, x,y in 0..199, and is included when its Euclidean distance from the
L2 centroid is <= 25 pixels. No convention is chosen from the outcome. A
conclusion that depends materially on the one-pixel convention is reported as
coordinate-sensitive.

## Fixed image diagnostics

For each context and frame, decode CAL and COR as big-endian float64 and retain
only finite values for diagnostics. Compute:

1. DEFAULT-radius sums for CAL, COR and DELTA = COR - CAL under C0 and C1.
2. Full-frame median and robust MAD scale of DELTA.
3. The corresponding smearing-row vector and the aperture-weighted smearing
   sum (each column value repeated for every aperture pixel in that column).
4. Outside a radius-35 target exclusion, fit the fixed two-parameter model
   `DELTA(y,x) = alpha + beta * SMEAR(x)` by ordinary least squares. Record
   alpha, beta and residual RMS. This is diagnostic only; no pixel is corrected
   with this fit.
5. For CAL, COR and DELTA aperture sums, fit the same LS7X sideband-only
   unweighted straight-line temporal baseline and report the three-row event
   excess relative to that baseline. The screening threshold is not re-applied
   to create a new candidate list.
6. Construct a per-pixel event excess map by fitting each pixel independently
   to the 24 fixed sideband frames versus time and summing event minus
   prediction over the three event rows. Record:
   - radius-25 event-excess sum under C0 and C1;
   - radius-35 excluded-region sum;
   - full-frame sum;
   - L1 concentration: sum(abs(excess)) inside r<=25 divided by full-frame
     sum(abs(excess));
   - column-coherence fraction: squared norm of the column-constant component
     divided by the squared norm of the complete excess map.

The same quantities are computed separately for CAL and COR. No outcome-driven
spatial mask, clipping threshold or smoothing is allowed.

## Interpretation gates

This follow-up may classify a cluster only at the following descriptive level:

- **CORRECTION_LINKED**: the event-minus-sideband change in DELTA aperture sum
  has magnitude >= 50% of the COR event excess in both C0 and C1, or the CAL
  and COR event-excess maps differ by a column-coherent component whose
  aperture contribution has magnitude >= 50% of the COR event excess in both
  conventions.
- **IMAGE_LOCALIZED_NOT_CORRECTION_DOMINATED**: the above gate is false and the
  COR event excess is positive in both conventions with >= 50% of the absolute
  COR excess-map L1 norm inside r<=25.
- **AMBIGUOUS_IMAGE_FOLLOWUP**: neither gate is met, conventions disagree, or
  required finite data are unavailable.

These labels do not classify an event as astrophysical or artificial.
`CORRECTION_LINKED` means only that the frozen L2 excursion is quantitatively
coupled to the DRP CAL->COR correction on these frames.

## Audit and stopping rule

An independent auditor must parse the saved byte ranges directly, rebuild the
frame indices and both coordinate conventions, and reproduce all continuous
summary quantities to fixed numerical tolerance plus the discrete descriptive
gate. Publication requires a passing audit.

Do not inspect other apertures, raw imagettes, unused rows or other visits as a
repair. If a cluster remains image-localized or ambiguous, the next step must
be separately frozen before any additional pixels are opened. Raw-imagette
`gcoadd` calibration remains a distinct unresolved path.
