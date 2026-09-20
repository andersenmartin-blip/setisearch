# Continue after LS8E target selection

The independent target/product selection is complete before new-target science
access.

## Frozen selection

Target: **GJ 876**.

Exact selected pair:

1. `CH_PR100018_TG032801_V0300`, OBSID 1201652, MJD 59077.4744239216.
2. `CH_PR100018_TG032802_V0300`, OBSID 1237379, MJD 59114.8053256116.

Both use PIPE 14.1.2 and 14 x 3.0-second exposures, giving a 42-second stacked
exposure, and both expose the required DEFAULT L2 light curve plus CAL and COR
subarrays. Seven GJ 876 visits meet the frozen eligibility rule; the pair above
is the two chronologically earliest, not a result-selected subset.

The metadata-only selection read zero science-product bytes, zero FITS table
rows and zero image pixels.

## Immediate next action

Perform one header-only preflight on the exact DEFAULT light curve for each
selected visit. Read 2880-byte FITS header blocks only through the first
`SCI_COR_Lightcurve` BINTABLE header. Require HTTP 206, exact range/length,
stable nonempty ETag and Content-Disposition, and cap each object at 64 KiB.

Record rows, row width, table offset/size, schema, aperture, NEXP, EXPTIME,
TEXPTIME, stacking, pipeline and time system. The preflight must end exactly at
the first table-data byte; **table data remain closed**.

If both headers establish the same compatible DEFAULT-L2 schema, publish that
metadata freeze and then freeze the two-visit L2 screen before opening any
table value. Reuse the LS7X/LS8A screen only if compatibility is established;
do not repair the method from GJ 876 outcomes.

Any later excursion remains an L2 diagnostic. Image follow-up requires its own
predeclared CAL/COR range scope. Raw imagettes remain outside this branch.

[Selection result](results_ls8e_selection/REPORT.md)
[Selection protocol](LS8E_TARGET_SELECTION_PROTOCOL.md)
