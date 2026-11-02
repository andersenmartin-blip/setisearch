# Independent batch05 numerical audit

Status: **PASS**. See `SUMMARY.json` for exact coverage and source hashes.

All available input products and selected science files were verified by hash and identity. Every saved event/order array was reconstructed from original products; raw counts, backgrounds, excess and native flux were compared exactly. Wavelengths and detector traces used independently implemented direct-power polynomials with explicit numerical tolerances. All global-grid orientation correlations/profiles and all five-window reference tests were recomputed without importing the production analysis modules.

The preserved two-sided local check was checked for coverage and gate arithmetic only; its full numerical reconstruction is not claimed. Shared numerical dependencies remain NumPy/SciPy/Astropy. This audit verifies extraction and accounting, not physical origin or visual classifications.

Run `python3 independent_audit/check_batch05.py` from the batch directory in a separate restored working copy without an existing audit summary. Original source products are required; preserve the published audit result.

The fixed batch covers **2 events in 1 exposure**, both mapping-supported. The audit verified **3 input files**, reconstructed both full cutouts, and recomputed **192 global region/orientation cases** plus **10 five-window references**. All **33 frozen source/code hashes** remained unchanged. `METHOD_ADAPTATION.json` documents the bookkeeping-only adaptation from the previous independent checker.

`ACQUISITION_INVENTORY.json` independently reconciles both canonical products and their per-product receipts with frozen jobs, source lengths/hashes, and the retained byte ledger: **27,804,441 known-returned and charged bytes**, two successful first attempts, no unknown-byte charges or noncanonical product files. Both product status lines and the final completion line are present in the retained stdout log. This checks retained records; it does not independently measure network traffic.

To reproduce the inventory in a separate restored working copy without the existing output: `python3 independent_audit/check_inventory.py`.
