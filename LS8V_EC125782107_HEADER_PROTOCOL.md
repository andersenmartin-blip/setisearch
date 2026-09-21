# LS8V — EC 12578-2107 DEFAULT-L2 header preflight

21 September 2026. Status: **EXACT PAIR AND HEADER SCOPE FROZEN BEFORE NEW HEADERS OR VALUES**.
This follows LS8U_CONTINUATION.md at `951e8cfd1cf008d259dabfb51534e2bc1fe18b4c`.

## Predetermined selection

EC 12578-2107 is rank 5 in the unchanged LS8J metadata-only first-1,000-row
chronology. Original selection: `81692343a774b19d26c28dd9596ad1dd1a31ef01`;
complete-inventory reconciliation: `f50fae88ba4f52b2d288a13feaaef2e8a069be29`.
Only the first two of its seven eligible visits are included:

| Exact product key | Archive start MJD | Ledger NEXP | Ledger EXPTIME / TEXPTIME |
|---|---:|---:|---:|
| CH_PR100002_TG008901_V0300 | 58957.7205977074 | 1 | 60 / 60 seconds |
| CH_PR100002_TG008902_V0300 | 58961.9356296883 | 1 | 60 / 60 seconds |

These are ledger metadata, not newly verified headers. The original full
product-response retention limitation and its separately dated reconciliation
remain explicit. Require unchanged complete 107-cohort order and equality of
entry 5 with config/ls8v_selected_pair.json. Pin the original census, selection,
reconciliation, reference schema, stable scorer, LS8S header reader and LS8U
continuation. No new target ranking, census or later visit is allowed.

## Exact metadata-only acquisition

The LS8V reader adapts LS8S only in target keys, paths, cohort index and expected
exposure tuples. URL resolution, HTTP validation, header parsing and budget
are unchanged. Verify the public freeze HEAD and clean tracked tree before
archive access. Read only the primary and first SCI_COR_Lightcurve BINTABLE
headers of the exact DEFAULT products, in 2,880-byte HTTP ranges, with a
64 KiB budget per product. Science-table bytes and image pixels remain zero.

Require HTTP 206, exact Content-Range and Content-Length, stable total size,
ETag and filename, exact key/version/DEFAULT suffix, SIMPLE=true, zero-axis
primary, correct BINTABLE EXTNAME, no heap and the complete pinned
18-column/138-byte schema. Independently verify both visits against their
own headers: PIPE_VER=14.1.2, NEXP=1, EXPTIME=TEXPTIME=60 seconds within
1e-6 seconds. Derive row counts and table boundaries from each header.
Do not infer them from durations or another visit.

Preserve every validated block and receipt immediately, including partial
results on failure. Publish headers, schemas, source identities, declared
ranges, logs, environment, run status and checksums. On an identity, transport,
schema or exposure mismatch, stop without substitute products or expanded
scope. Alternate apertures, images, raw imagettes and five later visits are
outside this scope.

## Separate value and follow-up freezes

Only after a public PASS_COMPATIBLE result, freeze the exact two DEFAULT-L2
table ranges and source identities before science values. Transfer the
unchanged hash-pinned LS8K scorer and independent scalar auditor: one/two/three
rows (expected 60/120/180 seconds), 12 baseline rows and two guards per side,
original finite/status/cadence eligibility, endpoints +/-8.5 and signed
clustering. Run the two existing stable-arithmetic known-answer tests first.
Preserve relative 2e-8 / absolute 2e-10 tolerances, both signs and every eligible
window. No LS8U residual measure, pixel rank, image label or correction becomes
a selection rule.

If neither sign crosses the endpoint, close this pair as a descriptive null;
the next independent cohort is rank-6 GJ 436, keys
CH_PR100041_TG000302_V0300 and CH_PR100041_TG001301_V0300, requiring its own
metadata-first freeze. If either sign forms clusters, retain all signed
representatives for one separately frozen CAL/COR diagnostic, with exact
metadata joins and image-byte limits before values. This header protocol
and subsequent L2 scope authorize no images. Resolve any audit failure using
retained data before further acquisition or promotion.

Scores are not Gaussian significances and overlapping windows are dependent.
No completeness, short-glint sensitivity, population limit, qualified SETI
candidate, detector or observing coverage follows from this descriptive
screen. The LS8U unresolved positive and all closed studies are preserved;
reserved TESS/M43 panels remain closed. The raw-imagette calibration gate
remains NOT_READY and its request unsent. Standing publication authorization
continues; delegation remains deferred.
