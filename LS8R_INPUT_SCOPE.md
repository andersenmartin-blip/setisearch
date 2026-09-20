# LS8R — all HD 136352 negative controls, paired-image metadata scope

Status: **FROZEN BEFORE NEW CAL/COR HEADERS, METADATA OR IMAGE ACCESS**.

The LS8Q two-visit screen is complete at
`69108d1939f5a1ed6a466d46f7376ed0f90dc2fb`: 1,125 rows, 1,923 eligible
overlapping windows, zero positive crossings, and 13 negative crossings
forming three clusters. All 23,076 independent numerical/discrete comparisons
pass without disagreements. Follow every signed representative from that
screen; all three happen to be negative. Scores are not Gaussian significances.

| Visit, V0300 | Sign | Cluster | Start row | Duration, stacked rows | Score | Context [start,stop) |
|---|---|---:|---:|---:|---:|---|
| CH_PR100041_TG000901 | negative | 0 | 46 | 1 | -13.440986490 | 32:61 |
| CH_PR100041_TG000901 | negative | 1 | 196 | 1 | -29.560654017 | 182:211 |
| CH_PR100041_TG000101 | negative | 0 | 432 | 2 | -15.244649337 | 418:448 |

Exact tuples and source hashes are in `config/ls8r_representatives.json`.
Verify the complete LS8Q result manifest and PASS, compare tuples with both
signed cluster lists, and verify pinned reader and image mathematics before
metadata acquisition. No added, missing or substituted representative.

## Headers and exposure metadata only

For the two exact visits, acquire only SCI_CAL_SubArray/SCI_COR_SubArray
FITS headers and SCI_CAL_ImageMetadata/SCI_COR_ImageMetadata tables. Retain
the existing reader with a strict 20,000,000-byte per-product budget checked
before transfer, HTTP 206 and exact range/length validation, stable source
size/ETag and exact product filenames. Preserve raw header/metadata ranges
and receipts. Skip all image/smearing arrays by declared FITS lengths.

Join **88 L2 context rows** to both CAL and COR: **176 unique joins**, <=1 ms
MJD and BJD differences, exact UTC text and matching exposure counter and
integrity fields. Require unscaled 200x200 float64 images, matching offsets
and BUNIT, and matching L2 PIPE_VER/NEXP/EXPTIME/TEXPTIME. Verified L2 exposure
values are PIPE 14.1.2, NEXP=26, EXPTIME=1.70000004768372 s and
TEXPTIME=44.2000007629395 s. Match the COR smearing-row layout as well.
One L2 row is a delivered 26-exposure stack, not a resolved 1.7-second image.

Derive frame indices from unique joins rather than assuming they equal L2
indices. The independent struct-decoder metadata audit must pass before
pixels. Publish source identities and exact future ranges in
`config/ls8r_images.json`; this metadata stage reads zero image values.
A mismatch stops the study without schema, tolerance or visit substitution.

## Conditional image stage under a separate freeze

After the metadata audit, freeze the exact image/smearing byte ranges in a
new protocol before payload access. Use unchanged paired-image mathematics,
classification order and all original gates: CORRECTION_LINKED first, then
SPATIALLY_STRUCTURED, otherwise UNRESOLVED_WITHIN_FIXED_SCOPE. Keep both
coordinate conventions, common finite mask, 12-row sidebands, two-row guards,
radius 25 aperture, 30<r<=40 annulus, column and smearing diagnostics.

Two representatives have one event row and the third has two; sum exactly
their original event rows. Keep all three results and known-answer tests
for both signal signs before payload. Require the unchanged independent
long-double/normal-equation reconstruction of maps, fits and labels. Transfer
no LS8P noise weighting, pixel deletion or hypothetical correction as a cut.

If all three close under the fixed descriptive gates, close this follow-up
and return to rank-4 TESS_260647166 in the existing CHEOPS target ledger under
its own metadata and exact science-byte freezes. If any remain unresolved,
state the specific limitation before one separately frozen retained-data
study; no automatic extra visits/pixels or candidate promotion. A label does
not identify a unique physical cause, artificial origin, detector qualification
or observing coverage. Closed GJ 1132/WASP-189 studies, raw imagettes and
reserved TESS/M43 data remain unchanged; the calibration request stays unsent.
