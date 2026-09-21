# LS8AA — WASP-43 DEFAULT-L2 header preflight

21 September 2026. **EXACT PAIR AND HEADER SCOPE FROZEN BEFORE NEW HEADERS OR VALUES**.
Continuation: LS8Z_CONTINUATION.md at
`62520522f1a4ac3bf0fc1e1b599200ef353be7b9`.

## Predetermined pair

WASP-43 is rank 8 of the unchanged LS8J metadata-only first-1,000-row
chronology. Original selection: `81692343a774b19d26c28dd9596ad1dd1a31ef01`;
full-inventory reconciliation: `f50fae88ba4f52b2d288a13feaaef2e8a069be29`.

| Exact product key | Ledger start MJD | Ledger NEXP | Ledger EXPTIME / TEXPTIME |
|---|---:|---:|---:|
| CH_PR100016_TG007801_V0300 | 58963.1705933163 | 1 | 60 / 60 seconds |
| CH_PR100016_TG007802_V0300 | 58966.4455962735 | 1 | 60 / 60 seconds |

These are the only two eligible visits in the original cohort.
Exposure values are ledger metadata, requiring separate FITS-header checks.
Require the complete original and reconciled 107-cohort orders to agree and
entry 8 to equal config/ls8aa_selected_pair.json. Preserve the original missing
full-response limitation and separately dated reconciliation. Do not requery,
extend or reorder the census. Pin the original selection, census,
reconciliation, reference schema, stable scorer, prior reader and continuation.

## Header-only acquisition and stopping rules

Transfer the LS8Y header reader, changing only keys, paths and cohort. Verify
the public freeze HEAD, clean tracked tree and all input pins before access.
Read the primary and first SCI_COR_Lightcurve BINTABLE headers of the two
exact DEFAULT products in 2,880-byte HTTP ranges, at most **64 KiB per product**.
Stop before table values. Preserve every block, identity and receipt.

Require HTTP 206, exact ranges/lengths, stable total size, ETag and filename,
the exact key/version/DEFAULT suffix, SIMPLE=true, a zero-axis primary,
the expected BINTABLE EXTNAME, no heap and the full pinned 18-column/138-byte
schema. Require PIPE_VER=14.1.2 and NEXP=1, EXPTIME=TEXPTIME=60 seconds
within 1e-6 seconds for each visit. Derive every row count and byte boundary
from its own header. Identity, schema, exposure or range failures stop.

Reuse the unchanged tested URL-resolution helper: at most three identical
resolution calls per product, original 45-second timeout, five-second spacing,
retry only TimeoutError including that exact wrapped URLError reason. Log
attempt, key, time and outcome without temporary URLs. Other errors stop
immediately. Run the five existing transport tests before archive requests.
Header-range requests are not retried. No alternate endpoint or product,
other aperture, later visit, image or raw imagette is authorized here.

Publish all headers, schemas, identities, declared ranges, attempt records,
environment, status, logs and checksums, including partial failures. No
result-dependent widening or substitution is permitted.

## Separate science and follow-up freezes

Only after a public PASS_COMPATIBLE result, freeze the exact DEFAULT-L2
table ranges and source identities. Transfer the unchanged hash-pinned
LS8K scorer and independent scalar auditor: one/two/three rows (expected
60/120/180 seconds), 12 sideband rows and two guards per side, original
finite/status/cadence eligibility, +/-8.5 endpoints and separate signed
clustering. Run the two existing stable-arithmetic tests before values.
Retain every eligible window and all signed representatives. Keep exact
discrete checks and relative 2e-8 / absolute 2e-10 audit tolerances.
The same declared helper may wrap science URL resolution; exact science
table requests remain unchanged and unretried.

If either sign has clusters, freeze the complete signed representative set
for a separate CAL/COR diagnostic, verify exact exposure joins, then freeze
exact image/smearing ranges before values. These header and L2 stages permit
zero image bytes. If neither sign crosses, close the pair as a descriptive
null and take the next cohort from the unchanged reconciled chronology with
its own header/science freezes. Preserve numerical failures and diagnose
retained inputs before any new acquisition or promotion.

Scores are not Gaussian significances; windows overlap. No sensitivity,
completeness, population limit, detector, qualified candidate or observing
coverage is established. No earlier residual measure, correction ratio or
image label becomes a new cut. PG 1245-042, GJ 436 and earlier bounded studies remain
closed; the earlier TESS_260647166 positive remains unresolved. Reserved
TESS/M43 panels remain closed, calibration is NOT_READY and its request
unsent. Standing publication authorization applies; delegation is deferred.
