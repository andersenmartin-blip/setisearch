# LS8O — all five GJ 1132 negative controls, paired-image metadata scope

Status: **FROZEN BEFORE CAL/COR HEADERS, METADATA OR IMAGE ACCESS**.

LS8N is complete and independently audited at
`4fb837cbe9744fe0a214e2a9da21fa26111cbb75`: 615 rows, 699 eligible windows,
zero positive clusters and five negative clusters. The unchanged independent
audit passes all 8,388 numerical/discrete comparisons. Follow **every** signed
cluster under the stopping rule, including the near-threshold negative case.
These scores are not Gaussian significances or SETI-candidate labels.

| Visit suffix (V0300) | Sign | Cluster | Start row | Duration | Score | Context, zero-based stop-exclusive |
|---|---|---:|---:|---:|---:|---|
| PR100041_TG000401 | negative | 0 | 88 | 3 | -8.529277829 | 74:105 |
| PR100041_TG000403 | negative | 0 | 69 | 3 | -17.739594988 | 55:86 |
| PR100041_TG000403 | negative | 1 | 132 | 3 | -9.164247856 | 118:149 |
| PR100041_TG000403 | negative | 2 | 191 | 3 | -9.124594182 | 177:208 |
| PR100041_TG000403 | negative | 3 | 297 | 3 | -8.838439333 | 283:314 |

The exact representative tuples and input hashes are frozen in
`config/ls8o_representatives.json`. Verify the entire LS8N checksum manifest
and PASS before new metadata acquisition. Check the tuples against both
complete published cluster lists. No added or substituted representative.

## Metadata-only stage

For exactly the two visits above, read only SCI_CAL_SubArray / SCI_COR_SubArray
FITS headers and their named SCI_CAL_ImageMetadata / SCI_COR_ImageMetadata
tables. Keep the existing range reader and its 20,000,000-byte per-product
header/metadata budget, with an explicit cumulative check **before** transfer.
Require HTTP 206, exact ranges, stable size/ETag and exact product filenames.
Retain raw header/table ranges and receipts. Skip all science and smearing
arrays by their declared FITS lengths; no raw imagette or alternate product.

Join **155 L2 context rows** to CAL and COR, requiring **310 unique joins**,
with <=1 ms MJD and BJD differences, identical UTC text and matching CAL/COR
exposure counters and integrity fields. Require 200x200 unscaled float64 image
planes, matching offsets/BUNIT, and PIPE version, NEXP=1 and 60-second exposure
keywords matching L2. Require a matching COR smearing-row layout. Derive native
frame indices from these joins; never assume equality with L2 row indices.

The independent struct-decoder audit must pass before image access. Publish
every source identity and future range in `config/ls8o_images.json`. A mismatch
stops the study with retained evidence; no visit/schema/tolerance substitution.

## Conditional image stage under a separate exact-range freeze

Reuse the unchanged LS8D/LS8H/LS8L paired-image mathematics and classification
order: CORRECTION_LINKED, SPATIALLY_STRUCTURED, UNRESOLVED_WITHIN_FIXED_SCOPE.
Keep common masks, sidebands, guards, original C0/C1 conventions and aperture
radii, CAL/COR/DELTA event maps, smearing/column diagnostics and the original
50% correction and 80%/20%-advantage displacement gates. No LS8M noise weights
or compactness cut is transferred. Three event rows are summed; they are not
treated as one exposure.

Publish a separate payload protocol and exact byte scope after the metadata
audit, then run known-answer tests before pixels. Keep all five outcomes and
both hypothetical signal signs in controls. If all close under the fixed
descriptive gates, close GJ 1132 and return to rank-3 HD 136352 under its own
new pair/header freeze. Any unresolved result requires its specific limitation
to be stated before a separately frozen retained-data study, with no automatic
widening or promotion. No new classifier, sensitivity/coverage qualification
or astrophysical/artificial origin claim follows. Reserved TESS/M43 inputs
and the separate unsent raw-imagette calibration request remain unchanged.
