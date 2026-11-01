# Independent batch03 numerical audit

Status: **PASS**. See `SUMMARY.json` for exact coverage and source hashes.

All available input products and selected science files were verified by hash and identity. Every saved event/order array was reconstructed from original products; raw counts, backgrounds, excess and native flux were compared exactly. Wavelengths and detector traces used independently implemented direct-power polynomials with explicit numerical tolerances. All global-grid orientation correlations/profiles and all five-window reference tests were recomputed without importing the production analysis modules.

The preserved two-sided local check was checked for coverage and gate arithmetic only; its full numerical reconstruction is not claimed. Shared numerical dependencies remain NumPy/SciPy/Astropy. This audit verifies extraction and accounting, not physical origin or visual classifications.

Run `python3 independent_audit/check_batch03.py` from the batch directory in a separate restored working copy without an existing audit summary. Original source products are required; preserve the published audit result.
