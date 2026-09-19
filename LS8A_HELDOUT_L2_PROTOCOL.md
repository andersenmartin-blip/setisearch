# LS8A — frozen held-out CHEOPS DEFAULT L2 transfer

Frozen 19 September 2026 after metadata-only preflight and before any table-data
byte from the held-out visit is read.

## Input fixed prospectively

Use exactly:
`CH_PR100006_TG000301_TU2020-12-01T14-08-40_SCI_COR_Lightcurve-DEFAULT_V0300.fits`

for file key `CH_PR100006_TG000301_V0300`, OBSID 1300462. This visit was
selected before its L2 rows were opened as the chronologically earliest public
55 Cnc visit after the March 2020 LS7X pilot.

Metadata freeze:

- total bytes: 184,320
- ETag: `"1679657116.7690594-184320-3324587187"`
- table starts at byte 20,160
- table payload: 162,564 bytes
- 1,178 rows, 138 bytes/row, 18 columns
- PIPE_VER=14.1.2, EXT_VER=13.1
- NEXP=20
- individual exposure = 2.21099996566772 s
- stacked TEXPTIME = 44.2200012207031 s
- DEFAULT aperture radius = 25 pixels
- FLUX/FLUXERR units = electrons.

## Unchanged LS7X screen

This is a transfer test of the existing screen in **cadence units**, not a
retuned 30/60/100-second search. Reuse unchanged:

- durations d = 1, 2, 3 consecutive rows;
- 12 sideband rows before and 12 after;
- 2-row guards;
- STATUS==0, finite BJD/FLUX/FLUXERR and FLUXERR>0 eligibility;
- every context gap in [0.5,1.5] × this visit's TEXPTIME;
- unweighted sideband-only straight-line baseline;
- sigma = max(1.4826×MAD residual, median FLUXERR,
  1e-12×abs(median sideband FLUX), 1e-12 electrons);
- the same OLS prediction-leverage denominator;
- positive threshold score >= +8.5;
- negative control score <= -8.5;
- positive clustering on overlapping events or separation <=1 row, with
  representative = highest score, then shorter duration, then earlier start.

The 44.22 s cadence means these durations correspond to approximately
44.22/88.44/132.66 s. No duration is added or removed because of that
difference.

## Boundary and stopping rule

Acquire only the already identified table payload using HTTP 206, exact
Content-Range, unchanged ETag, size and Content-Disposition. Do not inspect
another aperture or visit.

An independent struct/scalar auditor must rebuild every eligible window and
cluster without importing the producer scoring implementation. Publication
requires PASS.

A positive cluster is only an L2 excursion. It does not become a candidate
detection without separately frozen image-domain follow-up. A null is a
single held-out transfer result, not detector qualification or an occurrence
rate.
