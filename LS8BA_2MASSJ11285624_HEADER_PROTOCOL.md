# LS8BA — 2MASS J11285624+1010395 DEFAULT-L2 header preflight

23 September 2026. **EXACT PAIR AND HEADER SCOPE FROZEN BEFORE NEW HEADERS OR VALUES**.
Continuation: LS8AZ_CONTINUATION.md at
`dcb61841485349e90d3e221ba749f9da1f000e63`.

## Predetermined pair

2MASS J11285624+1010395 is rank 21 in the unchanged LS8J metadata-only
first-1,000-row chronology. Original selection:
`81692343a774b19d26c28dd9596ad1dd1a31ef01`; independent full-inventory
reconciliation: `f50fae88ba4f52b2d288a13feaaef2e8a069be29`.

| Exact key | Ledger start MJD | NEXP | Ledger EXPTIME / TEXPTIME, seconds |
|---|---:|---:|---:|
| CH_PR100018_TG010801_V0300 | 58973.0988567193 | 1 | 60 / 60 |
| CH_PR100018_TG010802_V0300 | 58976.88448678 | 1 | 60 / 60 |

These are both eligible visits for this target in the original ledger.
Require complete equality of the original and reconciled 107-cohort orders,
and entry 21 with config/ls8ba_selected_pair.json. Preserve the original
missing full-response limitation and separately dated reconciliation. Do not
requery, extend or reorder the census. Pin selection, census, reconciliation,
reference schema, stable scorer, prior reader/auditor and continuation.

## Own-header exposure and exact header scope

Transfer the LS8AX bounded reader and scalar header auditor with only paths,
keys, target, rank and prospectively fixed exposure encodings adapted.
Retain its exact binary32 ledger comparison: both visits independently require
EXPTIME and TEXPTIME to encode as `42700000`, corresponding to 60 seconds.
Also require NEXP=1, positive exposure, exact numeric EXPTIME=TEXPTIME in each
header and pipeline 14.1.2. Preserve the full FITS values and use each own
TEXPTIME for science cadence; no nominal value is substituted. A differing
encoding or tuple stops. The independent auditor has its own scalar FITS-card
decoder and explicit expected encoding, without importing the producer.

Verify public freeze HEAD, clean tracked checkout and every input pin before
access. Read only the primary and first SCI_COR_Lightcurve BINTABLE headers
of the two exact DEFAULT products in 2,880-byte HTTP ranges, at most **64 KiB
per product**. Stop before table values; retain every block and receipt.
Require HTTP 206, exact ranges and lengths, stable total size, ETag and filename,
the exact key/version/DEFAULT suffix, SIMPLE=true, zero-axis primary,
expected BINTABLE EXTNAME, no heap and the complete pinned 18-column/138-byte
schema. Derive each row count and byte boundary independently. Any identity,
schema, exposure or range failure stops without substitution.

Reuse the unchanged tested URL resolver: at most three identical resolution
calls per product, 45-second timeout, five-second spacing, retry only
TimeoutError including that exact wrapped URLError reason. Retain key,
attempt, timestamp and outcome without temporary URLs. All other errors stop.
Run the five existing transport tests before archive requests. Header-range
requests are not retried. No alternate endpoint, aperture, later visit,
image or raw imagette is authorized here.

Use the already verified sparse-checkout pattern and preservation guard from
LS8AX_CHECKOUT_RECOVERY.md. Checkout includes every pinned input and required
source/output directory; root files remain included. An incomplete checkout
cannot attempt a result commit. Publish headers, schemas, identities, declared
ranges, attempts, environment, status, logs and checksums, including failures.

## Separate science and follow-up freezes

After public PASS_COMPATIBLE, run the independently frozen scalar auditor on
retained headers to verify all receipts, complete schemas, exposure tuples
and byte boundaries. Only then freeze exact DEFAULT-L2 source identities and
table ranges before values. Transfer unchanged pinned LS8K scoring and the
independent scalar reconstruction: one/two/three rows using each verified
cadence, 12 sideband rows and two guards per side, original finite/positive-
error/STATUS=0/cadence eligibility, +/-8.5 endpoints and separate signed
clustering. EVENT remains metadata. Run both stable-arithmetic tests before
values. Keep every eligible window and signed representative, exact discrete
checks and relative 2e-8 / absolute 2e-10 numerical tolerances. Table ranges
remain unretried; only URL resolution can use the bounded resolver.

If either sign has clusters, freeze the complete signed representative set
for paired CAL/COR diagnostics, audit unique exposure joins, then separately
freeze exact image/smearing ranges before pixels. Header and L2 stages permit
zero image bytes. If neither sign crosses, close the pair within its eligible
scope and prepare rank-22 **GJ 422**, exact chronological pair
CH_PR100018_TG012201_V0300 / CH_PR100018_TG012202_V0300, under separate header
and science freezes. No target is chosen from its scientific outcome.
Preserve numerical failures and diagnose retained inputs before new access.

Scores are not Gaussian significances; windows overlap. No detector,
qualified candidate, sensitivity, completeness, population limit or observing
coverage is established. No prior result becomes a new cut. GJ 536's nine
original image labels, including P1/P6 unresolved, and its single bounded
study remain closed. Its three later visits stay outside the pair. Earlier
null scopes, unassessed points, unresolved labels and closed studies remain
unchanged. Reserved TESS/M43 panels stay closed. Calibration NOT_READY;
request UNSENT. Standing research/publication authorization applies;
delegation is deferred.
