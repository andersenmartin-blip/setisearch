# LS8I — exact GJ 649 DEFAULT-L2 header preflight

Status: **FROZEN BEFORE GJ 649 TABLE DATA**.

Exact products:
- `CH_PR100018_TG018601_V0300`
- `CH_PR100018_TG031201_V0300`

Read only the primary header and first `SCI_COR_Lightcurve` BINTABLE header
from the public DEFAULT lightcurve object for each exact file key. Use
2880-byte HTTP ranges, require HTTP 206, exact range lengths, stable object
size/ETag/Content-Disposition and <=64 KiB header transfer per product. Stop
before the first table-data byte.

Require V0300 / PIPE 14.1.2 and the required columns
`BJD_TIME, FLUX, FLUXERR, STATUS, EVENT`.

Preserve the selection-stage exposure contracts separately:

- TG018601: NEXP=1, EXPTIME≈22.65 s, TEXPTIME≈22.65 s;
- TG031201: NEXP=14, EXPTIME=3 s, TEXPTIME=42 s.

Record exact row count, row width, table-data start, declared table bytes and
full column schema. The schemas must be compatible with the unchanged
cadence-unit screen; cadence values themselves need not be equal.

If compatible, publish the header freeze before opening any science-table
value. Otherwise stop without substitution.
