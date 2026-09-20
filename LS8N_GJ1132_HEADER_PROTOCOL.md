# LS8N — independent GJ 1132 DEFAULT-L2 header preflight

Status: **PAIR AND HEADER SCOPE FROZEN BEFORE NEW HEADERS OR SCIENCE VALUES**.
Continuation is LS8M_CONTINUATION.md at
`0603b15168202af29aa1060fc5ae990201966b42`.

GJ 1132 is **rank 2** in the unchanged metadata-only LS8J first-1,000-public-row
chronological census. The original selection commit is
`81692343a774b19d26c28dd9596ad1dd1a31ef01`; the separate complete-inventory
reconciliation PASS is `f50fae88ba4f52b2d288a13feaaef2e8a069be29`.
Use the first two eligible visits already selected by that ledger:

| Exact file key | Archive start MJD | NEXP | EXPTIME / TEXPTIME |
|---|---:|---:|---:|
| CH_PR100041_TG000401_V0300 | 58934.9948654389 | 1 | 60 / 60 s |
| CH_PR100041_TG000403_V0300 | 58943.1171305167 | 1 | 60 / 60 s |

Verify pinned census, selection, reconciliation and reference-schema hashes.
Require the full reconciled cohort order to equal the original 107-cohort
order, and its second entry to equal the frozen configuration. Do not re-query
the census, choose a new visit or select using known signal behavior. The
original discarded inventory responses remain a historical limitation; the
separately dated reconciliation is not represented as original evidence.

## Header-only acquisition

Read only the primary and first SCI_COR_Lightcurve BINTABLE headers of each
exact DEFAULT product, with 2880-byte HTTP ranges and a strict **64 KiB budget
per product**. Require HTTP 206, exact byte range/length, stable total size,
ETag and Content-Disposition, and exact file-key/version/DEFAULT suffix.
Stop before the first science-table byte. Require zero-axis primary HDU,
SIMPLE=true, the correct BINTABLE EXTNAME, no heap, and a compatible
18-column, 138-byte schema identical to the published LS8K reference.

Require PIPE_VER=14.1.2 and both exposure tuples (NEXP, EXPTIME, TEXPTIME) to
equal (1,60,60), with absolute time tolerance 1e-6 s. Header content determines
row counts and offsets; they are not assumed from duration metadata.

Preserve every verified header block and receipt as it arrives, including
partial acquisition if later validation fails. Publish summaries, complete
schemas, exact source identities, row counts, declared table ranges, logs,
environment and checksums. A mismatch stops acquisition without substitution.
No light-curve values, alternate aperture, image, raw imagette or additional
visit is authorized by this header freeze.

## Next gate and unchanged scientific method

Only after a public PASS_COMPATIBLE preflight, freeze the two **exact science
byte ranges** and source identities in a separate commit before table access.
That screen transfers the unchanged stable LS8K method: 1/2/3 rows (60/120/180 s),
12 sideband rows each side, 2-row guards, full-context status/finite/cadence
checks, fixed +/-8.5 endpoints, both signed cluster sets, and unchanged
independent scalar audit with relative 2e-8 / absolute 2e-10 tolerances.
Run the existing known-answer stable-arithmetic tests first. LS8M's weights,
residual maps and compactness observations do not create new cuts or vetoes.

If the L2 screen is null, close this pair. If it has either sign of cluster,
retain all representatives and separately freeze their CAL/COR exposure joins
and exact image byte ranges before image access. Keep failures and nulls as
well as excursions. No detector/candidate/coverage qualification follows from
screening. Do not reopen WASP-189, reserved TESS sectors or M43 held-out panels.
The raw-imagette calibration gate and unsent technical request stay separate.
