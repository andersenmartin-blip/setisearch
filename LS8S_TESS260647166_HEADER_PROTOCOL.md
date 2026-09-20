# LS8S — independent TESS_260647166 DEFAULT-L2 header preflight

Status: **EXACT PAIR AND HEADER SCOPE FROZEN BEFORE NEW HEADERS OR VALUES**.
Continuation: LS8R_CONTINUATION.md at
`bfce990ec7710021e54a81f90027d733e37b4167`. HD 136352, GJ 1132 and WASP-189
follow-ups remain closed. TESS_260647166 is a CHEOPS archive target name;
this study does not open reserved TESS sectors.

The target is **rank 4** in the unchanged LS8J metadata-only first-1,000-row
chronological census. Selection commit:
`81692343a774b19d26c28dd9596ad1dd1a31ef01`; complete-inventory reconciliation
PASS: `f50fae88ba4f52b2d288a13feaaef2e8a069be29`. The existing first two
eligible visits are fixed below; the exposure entries are ledger metadata,
to be verified separately against each exact product header.

| Exact file key | Archive start MJD | NEXP | EXPTIME / TEXPTIME, seconds |
|---|---:|---:|---:|
| CH_PR300046_TG000101_V0300 | 58918.7572349357 | 1 | 42 / 42 |
| CH_PR100031_TG015701_V0300 | 58958.3675973350 | 1 | 49 / 49 |

The cohort has seven eligible visits; only these two are authorized here.
Verify the pinned original census, selection, reconciliation, reference
schema, stable scorer, previous metadata reader and current continuation.
Require equality of the complete original/reconciled 107-cohort order and
of its fourth entry with `config/ls8s_selected_pair.json`. Preserve the
original missing full-inventory-response limitation and the separately
dated reconciliation; do not rerun or reorder the census.

## Bounded metadata-only acquisition

Use the unchanged LS8Q URL, HTTP-range validation and header parsing
functions, with the two exact new keys and their different exposure tuples.
Verify freeze HEAD and a clean tracked tree before archive access. Read only
the primary and first SCI_COR_Lightcurve BINTABLE headers of the exact
DEFAULT products in 2,880-byte HTTP ranges, within **64 KiB per product**.

Require HTTP 206, exact range/length, stable total size, ETag and filename,
and the exact key/version/DEFAULT suffix. Stop before science-table bytes.
Require SIMPLE=true, a zero-axis primary, correct BINTABLE EXTNAME, no heap
and the pinned complete 18-column/138-byte schema. Require PIPE_VER=14.1.2,
NEXP=1 and both exposure times within 1e-6 seconds of **that visit's** ledger
values. Header-derived row counts and byte boundaries cannot be borrowed
from another visit, inferred from duration or adjusted after a mismatch.

Immediately preserve every verified block and receipt, including partial
results if a later check fails. Publish schemas, source identities, declared
table ranges, logs, environment, status and checksums. No substitute target
or product is selected after failure. Table values, alternate apertures,
images, raw imagettes and the five later visits remain outside this scope.

## Separate science-byte and image gates

After a public PASS_COMPATIBLE result, separately freeze the exact two table
ranges and source identities before values. Transfer the unchanged pinned
stable LS8K scorer and independent scalar auditor: durations one/two/three
rows, 12 baseline rows and two guards on each side, original finite/status/
cadence eligibility, endpoints ±8.5 and original signed clustering.
Durations are expected to be 42/84/126 seconds in the first visit and
49/98/147 seconds in the second, subject to exact header verification.

Run the existing two stable-arithmetic known-answer tests before values.
Keep relative 2e-8 / absolute 2e-10 audit tolerances. Preserve both signs,
all eligible windows, clusters and representatives. No previous residual
weight, image label, aperture change or hypothetical subtraction becomes
a screen cut or veto.

If both signs are empty, close this pair as a descriptive null and prepare
rank-5 EC 12578-2107 under a new metadata-first freeze. If either sign forms
clusters, retain every representative for a separately frozen CAL/COR
diagnostic; verify metadata joins before freezing exact image intervals.
This protocol and the subsequent L2 scope authorize no image access.
Preserve audit failures and resolve them on retained data before promotion.

Scores are not Gaussian significances, overlapping windows are dependent,
and no completeness, short-glint sensitivity, population limit, qualified
candidate, detector or observing coverage is claimed. Standing research and
publication authorization applies. The separate raw-imagette calibration
request remains unsent; reserved TESS/M43 data and closed studies stay closed.
