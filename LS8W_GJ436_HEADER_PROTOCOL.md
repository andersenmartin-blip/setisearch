# LS8W — GJ 436 DEFAULT-L2 header preflight

21 September 2026. **EXACT PAIR AND HEADER SCOPE FROZEN BEFORE NEW HEADERS OR VALUES**.
Continuation: LS8V_CONTINUATION.md at
`0a272628865396d354e72f9519d7b3a31b56fa7f`.

## Predetermined pair

GJ 436 is rank 6 of the unchanged LS8J metadata-only first-1,000-row chronology.
Original selection: `81692343a774b19d26c28dd9596ad1dd1a31ef01`; full-inventory
reconciliation: `f50fae88ba4f52b2d288a13feaaef2e8a069be29`. Its exact pair is:

| Product key | Ledger start MJD | Ledger NEXP | Ledger EXPTIME / TEXPTIME |
|---|---:|---:|---:|
| CH_PR100041_TG000302_V0300 | 58935.9974097329 | 1 | 60 / 60 seconds |
| CH_PR100041_TG001301_V0300 | 58962.4622264305 | 1 | 60 / 60 seconds |

These are the cohort's only two eligible visits in the original census.
Values above are ledger metadata; each FITS header must be checked separately.
Require the original and reconciled complete 107-cohort orders to agree and
entry 6 to equal config/ls8w_selected_pair.json. Preserve the original missing
full-response limitation and the separately dated reconciliation. Do not
requery, extend or reorder the census. Pin the census, selection,
reconciliation, reference schema, stable scorer and preceding continuation.

## Metadata-only acquisition

Use the LS8V header reader with only exact keys, paths and cohort changed,
plus the explicitly bounded URL-resolution timeout helper below. Verify the
public freeze HEAD and a clean tracked tree first. Read the primary and first
SCI_COR_Lightcurve BINTABLE headers of the exact DEFAULT products in 2,880-byte
HTTP ranges, with a **64 KiB budget per product**. Stop before table values.

Require HTTP 206, exact range/length, stable total size, ETag and filename,
exact key/version/DEFAULT suffix, SIMPLE=true, a zero-axis primary, expected
BINTABLE EXTNAME, no heap and the pinned complete 18-column/138-byte schema.
Require PIPE_VER=14.1.2, NEXP=1 and EXPTIME=TEXPTIME=60 seconds within 1e-6
seconds separately for both visits. Derive row counts and byte boundaries
from those headers; never borrow them from earlier visits or infer them from
the observing duration. Preserve each verified block and receipt immediately.

LS8V demonstrated a pre-data URL-resolution TLS timeout. For LS8W, before any
new headers or values, allow at most three calls of the same URL-resolution
request per exact product, each with its original 45-second timeout and a
five-second delay between retries. Retry only TimeoutError, including a wrapped
URLError whose reason is TimeoutError. All other failures stop. Log every
attempt with key, UTC time, outcome and error type; do not log temporary URLs.
The helper does **not** retry header-byte requests or science-table requests,
change endpoints, relax identity/schema gates or select alternate products.
Five synthetic transport tests must pass before any archive request: first
success, timeout then success, the three-attempt cap, non-timeout URL rejection
and immediate propagation of identity/schema assertions.

Publish headers, schemas, identities, declared ranges, attempt records, logs,
environment, status and checksums, including any partial failure. Stop on any
identity, schema, exposure, range or unrecovered transport failure; preserve
the outcome without new targets or broader input scope. Alternate apertures,
images, raw imagettes and all other visits remain outside this freeze.

## Separate science and image gates

Only after a public PASS_COMPATIBLE result, freeze exact DEFAULT-L2 table
ranges and source identities. Transfer the unchanged pinned LS8K stable
screen and independent scalar audit: one/two/three rows (expected 60/120/180
seconds), 12 sideband rows and two guards per side, original finite/status/
cadence eligibility, +/-8.5 thresholds and original separate signed clustering.
Run the two existing stable-arithmetic tests before values. Retain every
eligible window, both signs and original relative 2e-8 / absolute 2e-10 audit
tolerances. The same declared URL-resolution helper may wrap science URL
resolution; the exact table request itself remains unchanged and unretried.

If either sign produces clusters, retain all representatives in a separately
frozen CAL/COR diagnostic with exact metadata joins and image/smearing ranges
before values. This header scope and the subsequent L2 scope permit zero
image bytes. If both signs are empty, close this pair as a descriptive null;
next is rank-7 PG 1245-042, first pair CH_PR100002_TG008601_V0300 and
CH_PR100002_TG008602_V0300, requiring separate header and science freezes.
Any numerical audit failure is preserved and diagnosed on retained inputs.

Screen scores are not Gaussian significances; overlapping windows are
dependent. No completeness, short-glint sensitivity, population limit,
qualified candidate/detector or observing coverage follows. No previous
residual measure, image label or hypothetical correction becomes a new cut.
The prior unresolved TESS_260647166 positive and closed EC 12578-2107 result
are preserved. Other closed studies and reserved TESS/M43 panels stay closed;
the calibration gate is NOT_READY and its request unsent. Standing publication
authorization applies; delegation remains deferred.
