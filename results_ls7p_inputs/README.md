# LS7P retained reconstruction inputs

This package contains the 50 original input files retained from the explicit
15 September 2026 reconstruction of public freeze
`f42aa216b25779d55cd1fabd25545d3277abcfa5`. They are distinct from the missing
earlier original run. `SHA256SUMS` binds 49 files; the outer release inventory
also binds `SHA256SUMS` and this explanatory README.

`sources.json` and the twelve per-product JSON files preserve the selected
ranges, source URLs, ETags, lengths and SHA-256 receipts. `raw/` contains
lossless selected-pixel records, full sparse CR index payloads and the
separately selected CR records. The fixed acquisition budget was 140,176,892
science bytes. The full sparse index was used only to read cadence numbers
outside the selected contexts; unselected coordinates and amplitudes were
not interpreted. Full-product FITS checksums are not available from extracts.

The present completion uses these saved bytes offline and makes no additional
archive transfer. The original reconstruction acquisition console log is not
available; the receipt-bearing source ledger is retained unchanged. See the
[result](../results_ls7p_response/REPORT.md) and
[reproduction procedure](../results_ls7p_reconstruction/README.md).
