# LS8AU — LS IV +09 2 DEFAULT-L2 header preflight

23 September 2026. **EXACT PAIR AND HEADER SCOPE FROZEN BEFORE NEW HEADERS OR VALUES**.
Continuation: LS8AT_CONTINUATION.md at
`1456d0872722b29dc9bfc78961e5dc125edf5a58`.

## Predetermined pair

LS IV +09 2 is rank 17 of the unchanged LS8J metadata-only first-1,000-row
chronology. Original selection: `81692343a774b19d26c28dd9596ad1dd1a31ef01`;
full-inventory reconciliation: `f50fae88ba4f52b2d288a13feaaef2e8a069be29`.

| Exact product key | Ledger start MJD | Ledger NEXP | Ledger EXPTIME / TEXPTIME |
|---|---:|---:|---:|
| CH_PR100002_TG009301_V0300 | 58958.2321678431 | 1 | 60 / 60 seconds |
| CH_PR100002_TG009302_V0300 | 58974.0462928716 | 1 | 60 / 60 seconds |

These are the cohort's two eligible visits in the original census. Exposure
values require independent checks against each product's own FITS headers.
Require the original and reconciled 107-cohort orders to agree completely
and entry 17 to equal config/ls8au_selected_pair.json. Preserve the original
missing full-response limitation and separately dated reconciliation. Do not
requery, extend or reorder the census. Pin selection, census, reconciliation,
reference schema, scorer, prior reader/auditor and continuation.

## Header-only acquisition and stopping rules

Transfer the LS8AT reader, changing only keys, paths, cohort and rank; retain
the required exposure tuple (1, 60, 60). Verify public freeze HEAD, clean
tracked tree and all input pins before access. Read the primary and first
SCI_COR_Lightcurve BINTABLE headers of only these DEFAULT products in
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

After public PASS_COMPATIBLE, transfer the independent scalar FITS-card
auditor to the retained headers and verify every receipt, schema, exposure
tuple and row boundary. Only then freeze exact DEFAULT-L2 table ranges and
source identities. Transfer unchanged hash-pinned LS8K scorer and independent
scalar auditor: one/two/three rows (expected 60/120/180 seconds), 12 sideband
rows and two guards per side, original finite/status/cadence eligibility,
+/-8.5 endpoints and separate signed clustering. Both existing stable-arithmetic
tests pass before values. Retain every eligible window and signed representative.
Keep exact discrete checks and relative 2e-8 / absolute 2e-10 audit tolerances.
Science URL resolution may use the same helper; table ranges remain unretried.

If either sign has clusters, freeze the complete signed representative set
for CAL/COR diagnostics, verify exact exposure joins, then separately freeze
image/smearing ranges before pixels. Header and L2 stages permit zero image
bytes. If neither sign crosses, close the pair as a descriptive null and
take rank-18 GJ 9404 under its own header/science freezes. Preserve numerical
failures; diagnose retained inputs before new access or promotion.

Scores are not Gaussian significances; windows overlap. No sensitivity,
completeness, population limit, detector, qualified candidate or observing
coverage is established. No prior outcome becomes a new cut. EC 14599-2047
remains closed within eligible windows, with its unassessed late point and
third visit unchanged. GJ 581's 14 labels and bounded study remain closed,
including its two unresolved events. Other closed studies and reserved
TESS/M43 panels stay closed. Calibration NOT_READY; request UNSENT. Standing
research/publication authorization applies; delegation is deferred.
