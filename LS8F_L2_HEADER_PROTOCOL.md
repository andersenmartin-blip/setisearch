# LS8F — exact GJ 514 DEFAULT-L2 header preflight

Status: **FROZEN BEFORE GJ 514 TABLE DATA**.

Exact selected products:
- `CH_PR100018_TG007501_V0300`
- `CH_PR100018_TG007502_V0300`

For each, resolve only the public DEFAULT lightcurve object and read 2880-byte
blocks through the primary header and first `SCI_COR_Lightcurve` BINTABLE
header. Require HTTP 206, exact range/length, stable nonempty ETag and
Content-Disposition, identity encoding, and <=64 KiB header transfer.

The last acquired byte must be the last byte of the BINTABLE header. Table
data remain closed. Record schema, rows, row width, table start/size, columns,
PIPE_VER, NEXP, EXPTIME, TEXPTIME, aperture and time-system keywords.

Require V0300 / PIPE 14.1.2 and the selection-stage 2 x 22 s = 44 s exposure
contract. Required columns are BJD_TIME, FLUX, FLUXERR, STATUS and EVENT.

If both schemas are compatible, publish the header freeze before committing
the L2 screen. Otherwise stop without substituting another visit.

[Selection freeze](LS8F_TARGET_SELECTION.md)
