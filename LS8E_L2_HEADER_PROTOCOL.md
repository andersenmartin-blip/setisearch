# LS8E — exact GJ 876 DEFAULT-L2 header preflight

Status: **FROZEN BEFORE GJ 876 TABLE DATA**.

The metadata-only LS8E selection chose GJ 876 mechanically before science
access. This stage is restricted to the exact DEFAULT L2 light curves for the
two selected visits:

- `CH_PR100018_TG032801_V0300`
- `CH_PR100018_TG032802_V0300`

## Allowed access

For each exact file key, resolve only the public DEFAULT `lightcurves`
download object. Read 2880-byte FITS blocks starting at byte zero until the
primary header and the first `SCI_COR_Lightcurve` BINTABLE header are
complete.

Every byte request must require:

- HTTP 206;
- exact Content-Range and Content-Length;
- stable total object size;
- stable nonempty ETag;
- stable Content-Disposition;
- `Accept-Encoding: identity`.

Maximum header transfer is 64 KiB per object. The final acquired byte must be
the final byte of the first BINTABLE header. No table-data byte may be read.

## Required checks and outputs

Require the first extension to be `SCI_COR_Lightcurve` and record its row
count, row width, table-data start, declared table bytes, columns and these
keywords where present:

`EXT_VER, DATA_LVL, PROC_CHN, PIPE_VER, TIMESYS, T_STRT_U, T_STOP_U,
NEXP, EXPTIME, TEXPTIME, EXPT_TYP, AP_RADI, STACKING, ROUNDING, NLIN_COR,
APERTURE, CHECKSUM, DATASUM`.

The columns must contain at least
`BJD_TIME, FLUX, FLUXERR, STATUS, EVENT`. Both selected visits must retain
the selection-stage constraints: V0300, PIPE 14.1.2 and 42-second stacked
exposure.

Publish the raw 80-character header cards, exact receipts, object identity and
a combined summary. Record **table_data_bytes_acquired = 0**.

## Decision rule

If both products expose a compatible DEFAULT-L2 schema for the unchanged
cadence-unit screen, publish the header freeze. Only then may a separately
frozen L2 evaluation protocol be committed.

If either product is unavailable, changes identity, exceeds the header bound or
has an incompatible schema, stop and publish the obstruction. Do not substitute
another GJ 876 visit.

[Selection](results_ls8e_selection/REPORT.md)
[Continuation](LS8E_CONTINUATION.md)
