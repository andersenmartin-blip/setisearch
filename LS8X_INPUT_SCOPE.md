# LS8X — complete GJ 436 representative set, image metadata scope

21 September 2026. **FROZEN BEFORE NEW CAL/COR HEADERS, METADATA OR IMAGES**.

The audited LS8W result is `6038a0dfac58d9c74a6f88ce3afafda8eeffa1bf`:
640 rows, 936 eligible overlapping windows, **one positive crossing in one
cluster and zero negative crossings**. Both arithmetic tests and all
11,232 independent numerical/discrete checks pass. All 22 result files
were checksum verified and the L2 figure visually inspected.

| Exact visit | Sign | Cluster | Start row, zero-based | Duration | Score | Context [start,stop) |
|---|---|---:|---:|---|---:|---|
| CH_PR100041_TG000302_V0300 | positive | 0 | 33 | 1 row / 60 s | +9.634235209975396 | 19:48 |

This is the complete signed representative set. The second selected visit,
CH_PR100041_TG001301_V0300, has no crossing and does not require images.
Compare both visits' positive and negative cluster lists to the frozen
configuration before acquisition; do not add a below-threshold comparison
or replace this representative. The score is not Gaussian sigma. The event
and full context have EVENT OR=0, which remains metadata rather than a veto.

## Exact metadata-only scope

Pin the complete LS8W screen/header manifests, summary and independent audit,
the metadata reader, unchanged image mathematics, independent LS8T audit and
the previously tested timeout helper. Verify public freeze HEAD, a clean
tracked tree and every pin before access. Read only the exact first visit's
SCI_CAL_SubArray and SCI_COR_SubArray headers and their respective
SCI_CAL_ImageMetadata and SCI_COR_ImageMetadata tables. No second-visit
image product, new visit, alternative aperture or raw imagette is included.

Retain the original **20,000,000-byte budget per product checked before
transfer**, HTTP 206, exact byte range/length, stable total size/ETag and
exact filename. Preserve each header, table, receipt and partial result.
Skip all image and smearing values by their declared FITS lengths. This
stage permits **zero image pixels**.

Wrap only URL resolution with the unchanged, tested LS8W helper: at most
three identical requests per exact product, 45-second timeout, five-second
delay, retry only TimeoutError (or that wrapped URLError reason). Log every
attempt without temporary URLs. Serialize the two concurrent products' log
writes. No byte request, identity or schema gate is retried or weakened.

Join all **29 original L2 context rows** independently to CAL and COR:
**58 unique joins**, requiring <=1 ms MJD/BJD differences, exact UTC text
and agreeing exposure counters/integrity fields. Do not assume row-index
equality. Verify unscaled 200x200 float64 images, matching offsets/BUNIT,
and image/L2 equality of PIPE_VER=14.1.2, NEXP=1 and EXPTIME=TEXPTIME=60 s.
Check the COR smearing-row layout without reading its values.

The independent struct-decoder audit must pass before pixels. Its numerical
image-reconstruction functions are unchanged from LS8T; only paths and the
exact expected metadata-join count change. Publish joins, immutable source
identities and future byte intervals in `config/ls8x_images.json`, retaining
zero image bytes. On any mismatch, preserve the obstruction and stop without
new products, adjusted tolerances or changed joins.

## Conditional image stage after a separate payload freeze

After metadata/audit PASS, separately publish the exact image/smearing ranges,
all input hashes and unchanged paired-image diagnostic. Keep the common
finite mask, 12-row sidebands, two-row guards, both C0/C1 conventions,
r<=25 aperture, 30<r<=40 annulus and original column/smearing diagnostics.
The positive remains a one-row, 60-second event. Preserve gate order:
CORRECTION_LINKED, then SPATIALLY_STRUCTURED, otherwise
UNRESOLVED_WITHIN_FIXED_SCOPE. Reuse the existing nine synthetic tests
before payload; keep independent long-double/scalar reconstruction and
original numerical tolerances. No weighted residual, pixel removal,
alternative aperture or hypothetical subtraction becomes a new cut.

If this representative closes under the fixed descriptive gates, close the
GJ 436 pair and prepare rank-7 PG 1245-042 under separate metadata/science
freezes. If it remains unresolved, first identify the concrete limitation
before one separately frozen analysis of retained data. Do not acquire more
frames or visits merely to force a classification. Labels do not identify
unique physical causes or artificial origin; no qualified SETI candidate,
detector or observing coverage is claimed. Prior unresolved events, closed
studies and reserved TESS/M43 panels remain unchanged. Calibration is still
NOT_READY and its request unsent. Publication is already authorized.
