# LS8AT — EC 14599-2047 DEFAULT-L2 header preflight

23 September 2026. **EXACT PAIR AND HEADER SCOPE FROZEN BEFORE NEW HEADERS OR VALUES**.
Continuation: LS8AS_CONTINUATION.md at
`3cfada59a21d71242b8c42328063169e54a2a8b0`.

## Predetermined pair

EC 14599-2047 is rank 16 of the unchanged LS8J metadata-only first-1,000-row
chronology. Original selection: `81692343a774b19d26c28dd9596ad1dd1a31ef01`;
full-inventory reconciliation: `f50fae88ba4f52b2d288a13feaaef2e8a069be29`.

| Exact product key | Ledger start MJD | Ledger NEXP | Ledger EXPTIME / TEXPTIME |
|---|---:|---:|---:|
| CH_PR100002_TG010301_V0300 | 58966.1483766697 | 1 | 60 / 60 seconds |
| CH_PR100002_TG010302_V0300 | 58973.8976813102 | 1 | 60 / 60 seconds |

These are the first two of three eligible visits. TG010303 remains outside
this pair. Exposure values require independent checks against each product's
own FITS headers. Require the original and reconciled 107-cohort orders to
agree completely and entry 16 to equal config/ls8at_selected_pair.json.
Preserve the original missing full-response limitation and separately dated
reconciliation. Do not requery, extend or reorder the census. Pin selection,
census, reconciliation, reference schema, scorer, prior reader and continuation.

## Header-only acquisition and stopping rules

Transfer the LS8AQ reader, changing only keys, paths, cohort and rank; retain
the required exposure tuple (1, 60, 60). Verify public freeze HEAD, clean
tracked tree and all input pins before access. Read the primary and first
SCI_COR_Lightcurve BINTABLE headers of only the two DEFAULT products in
2,880-byte HTTP ranges, at most **64 KiB per product**. Stop before table
values. Preserve every block, source identity and receipt.

Require HTTP 206, exact ranges/lengths, stable total size, ETag and filename,
the exact key/version/DEFAULT suffix, SIMPLE=true, zero-axis primary,
expected BINTABLE EXTNAME, no heap and full pinned 18-column/138-byte schema.
Require PIPE_VER=14.1.2 and NEXP=1, EXPTIME=TEXPTIME=60 seconds within 1e-6
seconds for each visit. Derive row counts and byte boundaries separately.
Identity, schema, exposure or range failures stop without substitution.

Reuse the unchanged tested URL-resolution helper: at most three identical
resolution calls per product, original 45-second timeout, five-second spacing,
retry only TimeoutError including that exact wrapped URLError reason. Log
attempt, key, time and outcome without temporary URLs. Other errors stop
immediately. Run the five existing transport tests before archive requests.
Header-range requests are not retried. No alternate endpoint/product/aperture,
later visit, image or raw imagette is authorized here.

Publish all headers, schemas, identities, declared ranges, attempt records,
environment, status, logs and checksums, including partial failures.

## Separate science and follow-up freezes

Only after public PASS_COMPATIBLE and independent scalar FITS-card verification,
freeze exact DEFAULT-L2 table ranges and source identities. Transfer unchanged
hash-pinned LS8K scorer and independent scalar auditor: one/two/three rows
(expected 60/120/180 seconds), 12 sideband rows and two guards per side,
original finite/status/cadence eligibility, +/-8.5 endpoints and separate
signed clustering. Run both existing stable-arithmetic tests before values.
Retain every eligible window and all signed representatives. Keep exact
discrete checks and relative 2e-8 / absolute 2e-10 audit tolerances. Science
URL resolution may use the same declared helper; table ranges remain unretried.

If either sign has clusters, freeze the complete signed representative set
for CAL/COR diagnostics, verify exact exposure joins, then separately freeze
image/smearing ranges before pixels. These stages permit zero image bytes.
If neither sign crosses, close the pair as a descriptive null and take the
next unchanged cohort, rank 17 LS IV +09 2, under its own header/science
freezes. Preserve numerical failures; diagnose retained inputs before new access.

Scores are not Gaussian significances; windows overlap. No sensitivity,
completeness, population limit, detector, qualified candidate or observing
coverage is established. No earlier residual measure, correction ratio or
image label becomes a cut. GJ 581's 14 labels and bounded study remain closed,
including its two unresolved events; its five later visits remain outside
the original pair. Other closed studies and reserved TESS/M43 panels stay
closed. Calibration is NOT_READY and its request UNSENT. Standing research
and publication authorization applies; delegation is deferred.
