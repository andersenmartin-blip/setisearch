# Independent batch04 numerical audit

Status: **PASS**. See `SUMMARY.json` for exact coverage and source hashes.

All available input products and selected science files were verified by hash and identity. Every saved event/order array was reconstructed from original products; raw counts, backgrounds, excess and native flux were compared exactly. Wavelengths and detector traces used independently implemented direct-power polynomials with explicit numerical tolerances. All global-grid orientation correlations/profiles and all five-window reference tests were recomputed without importing the production analysis modules.

The preserved two-sided local check was checked for coverage and gate arithmetic only; its full numerical reconstruction is not claimed. Shared numerical dependencies remain NumPy/SciPy/Astropy. This audit verifies extraction and accounting, not physical origin or visual classifications.

Run `python3 independent_audit/check_batch04.py` from the batch directory in a separate restored working copy without an existing audit summary. Original source products are required; preserve the published audit result.

The audit covers all 94 selected records in 37 exposures. It independently reconstructed 122 complete cutouts from 36 available product pairs, accounted for two edge-truncated order records, and preserved V2E2-0332 and V2E2-0333 as unavailable. It checked 108 input hashes, 6,912 global region/orientation cases and 450 five-window references. The final mapping accounting is 80 supported records, 12 mapping-limited records and two unavailable records.

`ACQUISITION_INVENTORY.json` records an earlier byte/receipt-only inventory. `SUPPLEMENTAL_INVENTORY.json` additionally verifies canonical extraction pairs and the saved packages. Its accompanying `check_inventory.py` enumerates every noncanonical file in `products/`, including dot-prefixed names; only exact manifest products and known metadata receipts are excluded from that enumeration. All nine residual `.part` files (132,489,088 bytes, including three complete duplicates) match canonical prefixes and were excluded from analysis and the nine raw-input ZIPs and evidence archive. Their origin and any attribution to additional network bytes remain unknown.

The acquisition log contains 38 status lines for 72 canonical product receipts and no final `COMPLETE` line. Every logged identity agrees with the manifest, but 34 receipt identities are absent from the log. The original log is retained without reconstruction or an inferred cause. Per-product receipts and the complete canonical manifest supply the acquisition accounting.

Run `python3 independent_audit/check_inventory.py --check-packages` only in a separate restored copy without an existing inventory report, with the ZIPs available at the paths recorded in the local copy of `checkpoints/INPUT_ARCHIVES.json`. If ZIPs were restored elsewhere, adjust only those local `local_path` fields to the verified matching archives; retain filenames, sizes and hashes. Without `--check-packages`, the checker verifies canonical inputs, mapping accounting and noncanonical-file exclusions from analysis, and explicitly makes no package-exclusion claim. Clean restoration naturally contains no diagnostic residual files.

The first package-inventory attempt used an overly restrictive payload-only ZIP member assertion. The ZIPs correctly also contain canonical receipts, frozen restoration metadata and instructions. `inventory_attempt01.log` preserves that checker failure. The corrected checker verifies an exact whitelist of these members, compares their bytes with their sources, and confirms that no noncanonical payload entered either archive type. This correction changes no extraction, mapping, review threshold or scientific data.
