# LS8D paired-image study: metadata-first input scope

Continue from LS8C for all eight fixed representatives, with their unchanged
241 L2 context rows, 192 sideband rows, 32 guards and 17 event rows. This is
diagnostic follow-up of selected excursions, not a new held-out detector test.

First acquire headers and the SCI_CAL_ImageMetadata / SCI_COR_ImageMetadata
tables only, from SCI_CAL_SubArray and SCI_COR_SubArray for exactly:

- CH_PR100006_TG000302_V0300
- CH_PR100006_TG000303_V0300
- CH_PR100006_TG000304_V0300

Traverse FITS headers by their declared padded HDU lengths. Skip every image
array, including smearing arrays, during this preflight. Require HTTP 206 and
exact Content-Range, length and stable object ETag; never accept a whole-file
fallback. Reuse the established bounded LS7R header reader, narrowed to the
two named metadata tables, with a maximum 20 MB metadata/header transfer per
product. No raw imagettes, other aperture, fourth-visit image or new visit.

Use the native exposure timestamps and integration keywords to establish
unique CAL/COR joins for every fixed L2 context row. Verify image dimensions,
native coordinate offsets, pixel type/scaling, image units and product version.
Do not infer image-plane indices from L2 row indices alone. Persist identities,
header bytes, metadata bytes and the complete join ledger.

After this preflight, publish the exact paired-image byte/row scope, fixed
spatial region, diagnostics, closure/stopping rules, implementation and
known-answer tests before reading image payloads. Aim to perform acquisition,
paired-image/correction analysis, independent audit and publication as one
integrated study. If a required identity or join is unavailable, stop that
input explicitly rather than widening or guessing. The raw-imagette gate and
all previous results, including the original LS8B audit FAIL, are unchanged.
