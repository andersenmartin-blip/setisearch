# LS8AX — GJ 536 DEFAULT-L2 header preflight

23 September 2026. **EXACT PAIR AND HEADER SCOPE FROZEN BEFORE NEW HEADERS OR VALUES**.
Continuation: LS8AW_CONTINUATION.md at
`271c72c71afff7ba5bb3dee507e80931d11d3732`.

## Predetermined pair

GJ 536 is rank 20 of the unchanged LS8J metadata-only first-1,000-row chronology.
Original selection: `81692343a774b19d26c28dd9596ad1dd1a31ef01`;
full-inventory reconciliation: `f50fae88ba4f52b2d288a13feaaef2e8a069be29`.

| Exact product key | Ledger start MJD | NEXP | Ledger EXPTIME / TEXPTIME, seconds |
|---|---:|---:|---:|
| CH_PR100011_TG023501_V0300 | 58959.0929003754 | 1 | 40.1699981689453 / 40.1699981689453 |
| CH_PR100018_TG007801_V0300 | 58976.4945254206 | 1 | 40.2000007629395 / 40.2000007629395 |

These are the first two of five eligible visits. CH_PR100018_TG021001_V0300,
CH_PR100018_TG021002_V0300 and CH_PR100018_TG021003_V0300 stay outside the pair.
Require complete equality of the original and reconciled 107-cohort orders
and entry 20 with config/ls8ax_selected_pair.json. Preserve the original
missing full-response limitation and separately dated reconciliation. Do not
requery, extend or reorder the census. Pin selection, census, reconciliation,
reference schema, scorer, prior reader/auditor and continuation.

## Own-header exposure verification, fixed before access

The ledger values encode the IEEE-754 binary32 representations of nominal
40.17 and 40.20 seconds (up to their printed decimal precision). Freeze the
comparison at that exact representation: each product's own EXPTIME and
TEXPTIME must encode to the same binary32 bytes as their respective original
ledger fields, namely `4220ae14` and `4220cccd` in visit order. Require NEXP=1,
positive exposures and exact numeric EXPTIME=TEXPTIME in the FITS headers.
Pipeline must be 14.1.2. A different binary32 encoding stops the stage.

This prospective metadata representation check replaces the predecessor's
hard-coded 60-second tuple. It does not modify a science threshold or cadence
eligibility rule. Preserve the full unrounded FITS values and use each own
TEXPTIME for science cadence. Nominal 40.17/40.20 values are not substituted
for header values. The independent audit has its own scalar FITS-card decoder
and independently fixed expected encodings, without importing the producer.

## Header-only acquisition and stopping rules

Transfer the LS8AW bounded reader with only keys, paths, cohort, rank and the
declared exposure comparison changed. Verify public freeze HEAD, clean tracked
tree and input pins before access. Read only the primary and first
SCI_COR_Lightcurve BINTABLE headers of these DEFAULT products in 2,880-byte
HTTP ranges, at most **64 KiB per product**. Stop before table values.
Preserve every block, source identity and receipt.

Require HTTP 206, exact ranges/lengths, stable total size, ETag and filename,
the exact key/version/DEFAULT suffix, SIMPLE=true, zero-axis primary,
expected BINTABLE EXTNAME, no heap and full pinned 18-column/138-byte schema.
Derive row counts and byte boundaries separately. Identity, schema, exposure
or range failures stop without substitution.

Reuse the unchanged tested URL-resolution helper: at most three identical
resolution calls per product, original 45-second timeout, five-second spacing,
retry only TimeoutError including that exact wrapped URLError reason. Log
attempt, key, time and outcome without temporary URLs. Other errors stop
immediately. Run the five existing transport tests before archive requests.
Header-range requests are not retried. No alternate endpoint, product,
aperture, later visit, image or raw imagette is authorized here.

Publish all headers, schemas, identities, declared ranges, attempt records,
environment, status, logs and checksums, including partial failures.

## Separate science and follow-up freezes

After public PASS_COMPATIBLE, run the independent scalar FITS-card auditor
on retained headers, verifying all receipts, schemas, exposure tuples and
row boundaries. Only then freeze exact DEFAULT-L2 table ranges and source
identities. Transfer unchanged hash-pinned LS8K scorer and independent scalar
auditor: one/two/three rows using each verified cadence, 12 sideband rows and
two guards per side, original finite/status/cadence eligibility, +/-8.5 endpoints
and separate signed clustering. Both stable-arithmetic tests pass before values.
Keep every eligible window and signed representative, exact discrete checks
and relative 2e-8 / absolute 2e-10 numerical tolerances. Science URL resolution
may use the same helper; table ranges remain unretried.

If either sign has clusters, freeze the complete signed representative set
for CAL/COR diagnostics, verify exact exposure joins, then separately freeze
image/smearing ranges before pixels. Header and L2 stages permit zero image
bytes. If neither sign crosses, close the pair within its eligible scope and
take rank-21 2MASS J11285624+1010395 under separate header/science freezes.
Preserve numerical failures; diagnose retained inputs before new access or promotion.

Scores are not Gaussian significances; windows overlap. No sensitivity,
completeness, population limit, detector, qualified candidate or observing
coverage is established. No prior outcome becomes a new cut. EC14338-1445
remains closed within 63 eligible windows, with its large excluded signed
values unassessed. Earlier null scopes, unassessed points, unresolved labels
and closed studies remain unchanged. GJ 581 retains all 14 original labels,
including two unresolved events. Reserved TESS/M43 panels stay closed.
Calibration NOT_READY; request UNSENT. Standing research/publication
authorization applies; delegation is deferred.
