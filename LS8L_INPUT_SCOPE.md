# LS8L — all three WASP-189 excursions, paired-image metadata scope

Status: **FROZEN BEFORE CAL/COR IMAGE ACCESS**.

LS8K is complete and independently audited at
`ee35332b05edefc094a47cb6153fb9c05ea52289`. Retain every signed cluster,
with its originally selected representative. No additional event is selected.

| Visit suffix (V0300) | Sign | Cluster | Representative row | Duration | L2 score | Context (zero-based, stop-exclusive) |
|---|---|---:|---:|---:|---:|---|
| PR100041_TG000201 | positive | 0 | 521 | 1 | 8.982074701 | 507:536 |
| PR100041_TG000202 | positive | 0 | 678 | 1 | 60.894785514 | 664:693 |
| PR100041_TG000202 | negative | 0 | 119 | 1 | -23.271648387 | 105:134 |

These are L2 excursions, not Gaussian significances or SETI candidates.
The exact five-field representative tuples are fixed in
`config/ls8l_representatives.json` and checked against the complete published
LS8K cluster lists before joins are constructed.

## Metadata-only first stage

For the two exact visits, acquire only CAL/COR FITS headers and the named
SCI_CAL_ImageMetadata / SCI_COR_ImageMetadata tables. Use the existing
bounded reader: at most 20,000,000 header/metadata bytes per product, HTTP 206,
exact byte ranges, fixed total size and ETag, and exact product identities.
Skip all image and smearing arrays. Do not acquire another product or visit.

Join all 87 retained L2 context rows to unique CAL and COR exposures:
174 joins, each with <=1 ms MJD/BJD differences, equal UTC text and matching
CAL/COR CE counters and integrity values. Require matching detector offsets,
BUNIT, PIPE version, NEXP, EXPTIME and TEXPTIME, 200x200 float64 images,
unscaled pixel values and a matching COR smearing-row layout. Never equate
the image-plane index to the L2 row number without these joins.

Run the independent struct-decoder metadata audit before any image access.
If it passes, publish exact source identities and future byte ranges in
`config/ls8l_images.json`. If any check fails, preserve the obstruction and
stop without substituting a visit, event or matching tolerance.

## Conditional image stage, after public range freeze

Reuse the unchanged LS8D/LS8H paired-image mathematics and closure rules:
CAL, COR and DELTA=COR-CAL event maps; both coordinate conventions C0/C1;
r<=25 aperture, 30<r<=40 background annulus, r>35 smearing regression;
column-constant DELTA projection and brightness/displacement fits.

Classification order remains CORRECTION_LINKED, SPATIALLY_STRUCTURED,
UNRESOLVED_WITHIN_FIXED_SCOPE. Preserve all three signs and representatives,
including any unresolved result. Publish a separately fixed payload manifest
and image protocol before reading image bytes. Do not widen the closed scope
or adopt a new model/threshold in response to the images.
