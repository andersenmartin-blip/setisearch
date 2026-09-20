# LS8T — both TESS_260647166 signed representatives, image metadata scope

Status: **FROZEN BEFORE NEW CAL/COR HEADERS, METADATA OR IMAGE ACCESS**.

The complete audited LS8S result is
`cc05ba9a55a98bcfe6e1c747820ec4dd3265617f`: 1,747 rows, 2,004 eligible
overlapping windows, six positive crossings in one cluster and two negative
crossings in one cluster. Both arithmetic tests and all **24,048 independent
numerical/discrete comparisons** pass. Follow both original representatives;
neither their signs nor their durations are replaced after inspection.

| Visit, V0300 | Sign | Cluster | Start row | Duration, rows / integration | Score | Context [start,stop) |
|---|---|---:|---:|---|---:|---|
| CH_PR300046_TG000101 | negative | 0 | 317 | 3 / 126 s | -10.085104590 | 303:334 |
| CH_PR100031_TG015701 | positive | 0 | 217 | 1 / 49 s | 45.460348286 | 203:232 |

These are descriptive scores, not Gaussian significances. Both selected
contexts have EVENT OR=0; the flag remains metadata, not an extra cut.
`config/ls8t_representatives.json` pins the complete L2 manifest, summary,
audit and header manifest, metadata reader, image mathematics and prior
independent audit source. Verify every pin and the entire L2 manifest and
compare both signed cluster lists before metadata acquisition.

## Header and exposure metadata only

For the two exact visits, read only SCI_CAL_SubArray/SCI_COR_SubArray FITS
headers and SCI_CAL_ImageMetadata/SCI_COR_ImageMetadata tables. Reuse the
existing reader with its **20,000,000-byte per-product budget checked before
transfer**, HTTP 206, exact range/length validation, stable size/ETag and
exact product filenames. Preserve headers, metadata arrays, source receipts
and failed/partial results. Skip image and smearing values by declared FITS
lengths; do not read a pixel under this metadata scope.

Join all **60 fixed L2 context rows** independently to CAL and COR:
**120 unique joins**, with <=1 ms MJD/BJD differences, exact UTC text and
matching exposure counters/integrity fields. Verify unscaled 200x200
float64 images, matching offsets and BUNIT, and equality of image/L2
PIPE_VER, NEXP, EXPTIME and TEXPTIME for each visit. Verified L2 values are
PIPE 14.1.2 and NEXP=1 in both, with EXPTIME=TEXPTIME=42 seconds in
TG000101 and 49 seconds in TG015701. Check the COR smearing-row layout.

Derive image indices from unique joins rather than assuming equality with
L2 indices. The independent struct-decoder metadata audit must pass before
pixels. Publish identities, joins and exact future byte intervals in
`config/ls8t_images.json`, retaining zero image values read. On mismatch,
preserve the obstruction without changing schemas, tolerances or visits.

## Conditional image stage under a separate exact freeze

After the metadata audit, separately freeze the exact image/smearing payload
and immutable input hashes. Use the unchanged paired-image mathematics and
gate order: CORRECTION_LINKED, then SPATIALLY_STRUCTURED, otherwise
UNRESOLVED_WITHIN_FIXED_SCOPE. Preserve the common finite mask, both C0/C1
coordinate conventions, 12-row sidebands, two guards each side, r<=25
aperture, 30<r<=40 annulus, original models, column and smearing diagnostics.

The negative representative sums its original three 42-second exposures;
the positive uses its one 49-second exposure. Keep both results and run
known-answer tests of both signs, duration sums and guard exclusion before
payload. Use the unchanged independent long-double/scalar reconstruction
and original tolerances for maps, fits, memberships and labels. Transfer
no previous covariance weighting, pixel removal, alternative aperture or
hypothetical subtraction into a new cut.

If both events close under the fixed descriptive gates, close this pair
and prepare rank-5 EC 12578-2107 from the unchanged reconciled CHEOPS ledger
under new header and science-byte freezes. If either remains unresolved,
first state the concrete remaining limitation before one separately frozen
study of the retained data. Do not add pixels/visits or promote an event
because the descriptive gates fail. Stop this image stage after both cases.

No label uniquely determines physical or artificial origin; no qualified
candidate, detector or observing coverage is claimed. TESS_260647166 here
names CHEOPS products. Reserved TESS/M43 data, raw imagettes and closed
HD 136352/GJ 1132/WASP-189 studies remain unchanged. The separate calibration
request stays unsent. Standing research/publication authorization continues.
