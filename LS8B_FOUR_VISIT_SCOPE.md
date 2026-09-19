# LS8B — four-visit held-out CHEOPS L2 transfer suite: metadata freeze

Specified 19 September 2026 after the audited LS8A result and before any L2
table value from these visits is read.

## Deterministic visit selection

From the already published LS7R public 55 Cnc visit inventory, take the **next
four chronologically earliest public visits after LS8A**, without inspecting
their L2 values or substituting another visit if one is unavailable:

| order | archive visit id | OBSID | expected file key | start UTC |
|---:|---|---:|---|---|
| 1 | 100006000302 | 1310135 | CH_PR100006_TG000302_V0300 | 2020-12-17T04:51:00 |
| 2 | 100006000303 | 1310137 | CH_PR100006_TG000303_V0300 | 2020-12-18T07:19:00 |
| 3 | 100006000304 | 1319869 | CH_PR100006_TG000304_V0300 | 2020-12-24T18:07:00 |
| 4 | 100006000305 | 1319870 | CH_PR100006_TG000305_V0300 | 2020-12-25T20:34:00 |

Use only the official DEFAULT-aperture `SCI_COR_Lightcurve` for each visit.

## Metadata-only stage

For each exact file key, use the public DACE/CHEOPS lightcurve download
contract and acquire only 2880-byte FITS header blocks until the primary and
first BINTABLE header are complete. Require HTTP 206, stable ETag, exact
Content-Range, Content-Length and Content-Disposition. Cap each object at
64 KiB of header transfer.

Record file identity, total size, table offset/size, row count/width, columns,
PIPE_VER/EXT_VER, aperture radius, NEXP, EXPTIME and TEXPTIME.

**No table-data byte may be read in this stage.** If any exact DEFAULT product
is unavailable, publish that obstruction and do not replace it with another
visit.

## Later transfer rule, if all four metadata preflights pass

The eventual science evaluation must reuse the LS7X/LS8A cadence-unit screen
unchanged: 1/2/3 rows, 12+12 sidebands, two-row guards, unchanged STATUS/gap
eligibility, same local linear baseline/noise statistic, +/-8.5 thresholds and
same positive clustering. The visit-specific TEXPTIME changes physical
duration but does not authorize retuning.

The suite's primary method output is the **per-visit positive-cluster and
negative-control behavior**, with raw window counts retained for transparency.
Overlapping windows are not independent and must not be turned into a formal
false-alarm probability.

No image follow-up is automatic. Any positive excursion requires a separately
frozen diagnostic stage after the suite result is known.
