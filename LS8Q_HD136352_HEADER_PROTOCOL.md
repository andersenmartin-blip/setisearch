# LS8Q — independent HD 136352 DEFAULT-L2 header preflight

Status: **EXACT PAIR AND HEADER SCOPE FROZEN BEFORE NEW HEADERS OR VALUES**.
Continuation: LS8P_CONTINUATION.md at
`db109b68db843ee6d9ac51052372c84329668527`. The GJ 1132 and WASP-189 bounded
follow-ups remain closed.

HD 136352 is **rank 3** in the unchanged metadata-only LS8J first-1,000-public-row
chronological census. The selection commit is
`81692343a774b19d26c28dd9596ad1dd1a31ef01`; the complete-inventory
reconciliation PASS is `f50fae88ba4f52b2d288a13feaaef2e8a069be29`.
Use the first two eligible visits in that existing order:

| Exact file key | Archive start MJD | NEXP | EXPTIME / TEXPTIME, seconds |
|---|---:|---:|---:|
| CH_PR100041_TG000901_V0300 | 58943.6307305439 | 26 | 1.70000004768372 / 44.2000007629395 |
| CH_PR100041_TG000101_V0300 | 58953.6827227982 | 26 | 1.70000004768372 / 44.2000007629395 |

Verify the pinned original census, selection, reconciliation, reference schema,
stable scorer, previous metadata reader and continuation. Require exact equality
of the entire reconciled 107-cohort order with the original and of its third
entry with config/ls8q_selected_pair.json. Six visits are eligible in the
existing HD 136352 cohort; only the two selected visits are authorized here.
Do not repeat the census, reorder hosts or select by observed signal behavior.
The original missing full inventories remain a historical limitation; the
separate reconciliation retains fresh inventories without replacing history.

## Bounded headers only

Use the unchanged LS8N header request, range validation and parsing functions,
with the new exact keys and exposure checks. Verify the executing freeze HEAD
and a clean tracked tree before archive access. Read only primary and first
SCI_COR_Lightcurve BINTABLE headers of the exact DEFAULT products, in 2880-byte
HTTP ranges, with a strict **64 KiB per-product budget**.

Require HTTP 206, exact byte range and length, stable total size, ETag and
Content-Disposition, and the exact file key/version/DEFAULT suffix. Stop
before the first science-table byte. Require SIMPLE=true, zero-axis primary,
correct BINTABLE EXTNAME, no heap, and the pinned 18-column/138-byte schema.
Require PIPE_VER=14.1.2, NEXP=26, and both exposure times within 1e-6 seconds
of the frozen ledger values above. Let verified headers determine row counts
and byte offsets; do not infer them from visit durations.

Preserve verified blocks and receipts immediately, including partial results
if a later gate fails. Publish complete schemas, source identities, declared
table ranges, checksums, logs and execution status. A mismatch stops without
substitution. Science values, alternative apertures, images, raw imagettes
and the four later visits are outside this freeze.

## Separate science-byte gate

Only after a public PASS_COMPATIBLE header result, freeze the exact two
table ranges and identities before acquisition. Transfer the unchanged
hash-pinned LS8K/LS8N stable DEFAULT-L2 score and independent scalar audit:
one/two/three rows, 12 baseline rows per side, two guard rows, original
status/finite/cadence rules and endpoints +/-8.5. The integration windows
are expected to be approximately 44.2/88.4/132.6 seconds, subject to header
verification. Use TEXPTIME rather than individual EXPTIME for cadence.

Run the existing stable-arithmetic known-answer tests before table values.
Keep relative 2e-8 / absolute 2e-10 audit tolerances, both signed cluster sets,
and all representative/eligibility rules. Neither LS8M nor LS8P residual
weights, masks or hypothetical subtractions are screening cuts.

If both signed cluster sets are empty, close this pair as a descriptive null
and move to the next unchanged ledger cohort under a new freeze. If either
sign appears, retain all representatives and separately freeze CAL/COR
metadata joins before exact image ranges. Do not acquire images under this
header or subsequent L2-only scope. On failure preserve the outcome.

No screening score is a Gaussian significance, no short-glint sensitivity or
population limit is established, and no qualified detector, candidate or
observing coverage is claimed. Reserved TESS/M43 data and raw imagettes
remain closed. The separate calibration request remains unsent. Standing
research/publication authorization applies; no person-directed contact occurs.
