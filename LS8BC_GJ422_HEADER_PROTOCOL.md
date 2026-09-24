# LS8BC — GJ 422 DEFAULT-L2 header preflight

24 September 2026. **EXACT PAIR AND HEADER SCOPE FROZEN BEFORE HEADERS OR VALUES**.
Continuation: LS8BB_CONTINUATION.md at
`0b230cf296062893045d5cf04ba22d1e2cbeee36`.

## Predetermined pair

GJ 422 is rank 22 in the unchanged LS8J metadata-only first-1,000-row
chronology. Original selection: `81692343a774b19d26c28dd9596ad1dd1a31ef01`;
independent reconciliation: `f50fae88ba4f52b2d288a13feaaef2e8a069be29`.

| Exact key | Ledger start MJD | NEXP | Ledger EXPTIME / TEXPTIME, seconds |
|---|---:|---:|---:|
| CH_PR100018_TG012201_V0300 | 58977.1106305392 | 1 | 60 / 60 |
| CH_PR100018_TG012202_V0300 | 58981.0175723509 | 1 | 60 / 60 |

These are both eligible visits for this target in the original ledger.
Require equality of all 107 original and reconciled cohorts and exact entry
22 with config/ls8bc_selected_pair.json. Do not requery, extend or reorder the
census. Preserve the original missing-full-response limitation and its later
reconciliation. Input pins include the census, selection, reconciliation,
reference schema, stable scorer, timeout helper, prior reader/auditor and
latest continuation.

## Own headers only

Transfer the LS8BA bounded reader and independent scalar FITS-card auditor
with only target, keys, rank and paths adapted. Both visits independently
require NEXP=1, positive and exactly equal EXPTIME/TEXPTIME, pipeline 14.1.2,
and IEEE-754 binary32 encoding `42700000` for both exposure values, matching
the original ledger. Preserve full header values and use each own TEXPTIME
as its science cadence. A different tuple or encoding stops.

Require public freeze HEAD, clean tracked checkout and all input pins before
access. Read only the primary and first SCI_COR_Lightcurve BINTABLE headers
of these exact DEFAULT products in 2,880-byte ranges, at most 64 KiB per
product. Retain every block and receipt. Require HTTP 206, exact ranges and
lengths, stable total size, ETag and filename, exact key/version/DEFAULT
suffix, SIMPLE=true, zero-axis primary, expected BINTABLE EXTNAME, no heap,
and the complete pinned 18-column/138-byte schema. Derive each own row count
and byte boundary. No science-table or image values may be read here.

Reuse the unchanged timeout-only URL resolver: at most three identical
45-second calls per product, five-second spacing, retry only TimeoutError
including that exact wrapped URLError reason. Preserve attempts without
temporary URLs. Run the five existing transport tests before requests.
Header-range requests are not retried. Identity/schema failures stop without
substitution, extra endpoints, apertures or visits.

Use the established sparse checkout with every pin and required input/output
directory included. Preservation is conditional on checkout success. Publish
headers, summaries, identities, schemas, byte ranges, attempts, logs,
environment, status and checksums, including failures.

## Conditional next stage and stopping

After public PASS_COMPATIBLE, independently decode the retained FITS cards
and verify every manifest entry, receipt, complete schema, exposure tuple
and byte boundary. The auditor is frozen before headers and imports no
producer. Then separately freeze exact DEFAULT-L2 identities and ranges
before values. Transfer unchanged LS8K scoring and its independent scalar
audit: one/two/three rows at each own cadence, 12-row sidebands, two guards,
finite BJD/FLUX/FLUXERR, positive error, STATUS=0 throughout, and adjacent
cadences within 0.5–1.5 own cadence. EVENT remains metadata. Keep +/-8.5
endpoints, separate signed clustering and all eligible windows. Run both
stable-arithmetic tests before values; retain exact discrete checks and
relative 2e-8 / absolute 2e-10 tolerances.

If either sign has clusters, separately freeze the complete signed set for
paired CAL/COR metadata, independently audit unique exposure joins, then
freeze exact image/smearing ranges before pixels. Do not select only the
largest positive event. If neither sign crosses, close within eligible scope
and prepare rank-23 GJ 494, exact first pair CH_PR100018_TG007401_V0300 /
CH_PR100018_TG007402_V0300, under new header/table freezes. Its other two
visits remain outside that pair. Preserve failures before any new access.

Scores are not Gaussian significances; windows overlap. No qualified SETI
candidate, detector, sensitivity, population limit, completeness or observing
coverage is established. Prior labels, unassessed points, closed studies
and reserved TESS/M43 panels stay unchanged. Calibration NOT_READY; request
UNSENT. Standing research/publication authorization applies; delegation is
deferred.
