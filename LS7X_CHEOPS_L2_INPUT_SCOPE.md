# LS7X — CHEOPS DEFAULT L2 light-curve metadata preflight

Specified 19 September 2026 after LS7P publication completion and the public
CHEOPS source/DRP reconciliation. LS7X is a **new prospective continuation**.
It is not a reconstruction or replacement of the earlier local LS7W analysis,
whose exact eight artifact bytes are not available in the current workspace.

## Purpose

Establish the exact public structure and provenance of one fixed CHEOPS L2
light curve before any native flux value is inspected. This preflight exists
only to support a later, separately frozen short-transient pilot.

The fixed visit is:

- file key: `CH_PR300024_TG000301_V0300`
- target: 55 Cnc
- OBSID: 1015522
- visit date: 9 March 2020

The fixed product is the official DRP **DEFAULT-aperture**
`SCI_COR_Lightcurve`. The DEFAULT aperture is selected prospectively because
it is the pipeline's named default product; no R15–R40, RINF, RSUP or
outcome-selected aperture is inspected for primary selection.

## Strict metadata-only acquisition

Use the public DACE/CHEOPS download contract with:

- `file_type='lightcurves'`
- `aperture='default'`
- exact `file_key` equality.

Read only enough exact HTTP byte ranges to decode the primary FITS header and
the first table-extension header. Require HTTP 206, exact Content-Range,
stable ETag, exact byte count and a total transfer budget of **64 KiB**.

Do **not** read any table data bytes. In particular, no values from `FLUX`,
`FLUXERR`, `STATUS`, `EVENT`, `BACKGROUND`, centroid, roll angle or
time-series rows may be decoded at this stage. The preflight records column
names/formats/units and timing/header keywords only.

The script must stop after the BINTABLE header. It must assert that the table
data start lies strictly after the final acquired byte. Save the exact header
bytes and HTTP range receipts for audit.

## Fixed questions

Record, without inspecting rows:

1. exact filename, total byte size, ETag and FITS checksum metadata;
2. DRP/data-structure version and product level;
3. table row count and bytes per row;
4. all column names, FITS formats and units;
5. time system/reference and declared cadence/exposure fields;
6. DEFAULT aperture metadata and reduction-status keywords;
7. whether the table schema exposes the required flux/error/status/event and
   diagnostic columns for a later fixed pilot.

No detection threshold, sideband length, quality mask or candidate rule is
chosen from this metadata result. Those rules are frozen separately after the
structure is known and before table bytes are opened.

## Boundary

This stage adds zero science measurements, zero native transient trials, zero
candidate decisions and zero qualified observing seconds. It does not resolve
raw-imagette `gcoadd` or reproduce DRP 14.0.1 calibration. It tests a
different route: using the mission-delivered, already reduced L2 product for a
bounded native pilot while raw-imagette calibration remains separately open.
