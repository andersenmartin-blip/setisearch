# LS8G — exact GJ 849 DEFAULT-L2 header preflight

Status: **FROZEN BEFORE GJ 849 TABLE DATA**.

Exact products:
- `CH_PR100018_TG032401_V0300`
- `CH_PR100018_TG032402_V0300`

Read only the primary header and first `SCI_COR_Lightcurve` BINTABLE header
from the public DEFAULT lightcurve objects in 2880-byte ranges, with stable
ETag and Content-Disposition, HTTP 206, exact range lengths and <=64 KiB per
object. Stop before the first table-data byte.

Require V0300 / PIPE 14.1.2, NEXP=14, EXPTIME=3 s, TEXPTIME=42 s, and required
columns BJD_TIME, FLUX, FLUXERR, STATUS and EVENT. Record the exact table start,
row count, row width, declared byte count and schema.

If both products are compatible, publish PASS_COMPATIBLE before freezing the
unchanged symmetric 1/2/3-row screen. Otherwise stop without substitution.
