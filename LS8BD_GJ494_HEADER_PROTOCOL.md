# LS8BD — GJ 494 DEFAULT-L2 header preflight

24 September 2026. **EXACT PAIR AND HEADER SCOPE FROZEN BEFORE HEADERS OR VALUES**.
Continuation: LS8BC_CONTINUATION.md at
`5682ab2ea03835f4b945a95511fb976b768e5579`.

## Predetermined pair

GJ 494 is rank 23 in the unchanged first-1,000-row CHEOPS metadata census.
Original selection: `81692343a774b19d26c28dd9596ad1dd1a31ef01`; independent
reconciliation: `f50fae88ba4f52b2d288a13feaaef2e8a069be29`.

| Exact key | Ledger start MJD | NEXP | Ledger EXPTIME / TEXPTIME, seconds |
|---|---:|---:|---:|
| CH_PR100018_TG007401_V0300 | 58972.950558862 | 1 | 42 / 42 |
| CH_PR100018_TG007402_V0300 | 58982.7820436582 | 1 | 42 / 42 |

These are the chronological first two of four eligible visits. TG007403 and
TG007404 stay outside this pair. Require exact equality of all 107 original
and reconciled cohorts and entry 23 with config/ls8bd_selected_pair.json.
Do not requery, expand or reorder the census. Preserve the original
missing-full-response limitation and separately dated reconciliation.

## Own headers only

Transfer the LS8BC bounded reader and independent scalar FITS-card auditor
with only target, keys, rank, paths and prospective exposure encoding changed.
Each visit independently requires NEXP=1, positive and exactly equal
EXPTIME/TEXPTIME, pipeline 14.1.2, and IEEE-754 binary32 encoding `42280000`
for both exposure values, matching 42 seconds in the original ledger.
Preserve full FITS values and use each own TEXPTIME as science cadence;
do not inherit the previous target's 60 seconds. Any tuple/encoding mismatch
stops. The auditor has its own scalar parser and explicit expected encoding.

Require public freeze HEAD, clean tracked checkout and all ten input pins
before access. Read only primary and first SCI_COR_Lightcurve BINTABLE
headers of these exact DEFAULT products in 2,880-byte ranges, at most 64 KiB
per product. Preserve all blocks and receipts. Require HTTP 206, exact
ranges/lengths, stable total, ETag and filename, exact key/version/DEFAULT
suffix, SIMPLE=true, zero-axis primary, expected BINTABLE EXTNAME, no heap,
and the full pinned 18-column/138-byte schema. Derive own rows and boundaries.
No science-table or image values may be read here.

Reuse the unchanged timeout-only URL resolver: at most three identical
45-second calls per product, five-second spacing, retry only TimeoutError
including that exact wrapped URLError reason. Log every attempt without
temporary URLs. Run all five existing transport tests before archive access.
Range requests are not retried. All other failures stop without substitution,
extra endpoints, apertures or visits. Use the established sparse checkout
with all pins and required inputs/outputs; preservation requires successful
checkout. Publish headers, metadata, receipts, attempts, logs, environment,
status and checksums, including failures.

## Conditional science freeze and stopping

After public PASS_COMPATIBLE, independently verify every retained manifest
entry, receipt, full schema, exposure tuple and boundary with the frozen
scalar auditor. Then separately freeze exact DEFAULT-L2 identities/ranges
before values. Transfer unchanged LS8K scoring and independent scalar audit:
one/two/three rows at each own cadence, 12-row sidebands, two-row guards,
finite BJD/FLUX/FLUXERR, positive error, STATUS=0 throughout and adjacent
steps within 0.5–1.5 own cadence. EVENT remains metadata. Retain +/-8.5
endpoints, separate signed clustering and every eligible window. Run both
stable-arithmetic tests before values; preserve exact discrete checks and
relative 2e-8 / absolute 2e-10 tolerances.

If either sign crosses, separately freeze the complete signed representative
set for paired CAL/COR metadata; independently audit unique exposure joins,
then freeze exact image/smearing ranges before pixels. Do not select only
the strongest positive event. If neither sign crosses, close within eligible
scope and prepare rank-24 **2MASS J11474440+0048164**, exact pair
CH_PR100018_TG007101_V0300 / CH_PR100018_TG007102_V0300, under new header/table
freezes. A zero-eligible visit supplies no tested null. Preserve numerical
failures before new access or promotion.

Scores are not Gaussian significances and windows overlap. No qualified SETI
candidate, detector, sensitivity, completeness, population limit or observing
coverage is established. Previous labels, unassessed points, closed studies,
cohort order and reserved TESS/M43 panels stay unchanged. Calibration
NOT_READY; request UNSENT. Standing research/publication authorization
continues; delegation is deferred.
