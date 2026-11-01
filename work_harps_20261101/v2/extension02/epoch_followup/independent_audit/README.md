# Independent epoch-follow-up audit

Result: **PASS_INDEPENDENT_SCALAR_AND_COVERAGE_AUDIT**, with no discrepancies beyond floating-point rounding.

- All100 input FITS SHA-256 values match both the fixed plan and acquisition manifest. Their barycentric air wavelengths in angstrom, single-exposure metadata, ADU units and BERV values were checked.
- All336 catalog IDs appear once in the result list. Every same-target exposure within extension02 appears in both frames, for4,370 profiles /2,185 event–epoch pairs. All profile hashes and requested wavelength transforms were verified.
- All336 event summaries were recomputed from their complete measurement tables. Discovery exposures are excluded from other-epoch statistics, leaving3,698 comparison frame records.
- Separate scalar calculations reconstructed50 complete profiles for V2E2-0001, V2E2-0169, V2E2-0336 and V2E2-0005, including eight low-continuum profiles. This covers interpolation, normalization, first-difference MAD proxy, sideband linear fits, narrow/broad signed Gaussian amplitudes and RMS, integrated residuals and discovery correlations.

The largest raw-flux difference was1.82×10⁻¹² ADU. Gaussian amplitude differences were at most2.67×10⁻¹⁵; correlation differences were at most5.56×10⁻¹⁶. Production files were unchanged throughout the audit.

The checker never imports the production measurement module. It uses scalar bisect interpolation, Python statistics, closed-form sideband regression, scalar pivoted normal equations and math.fsum correlations. It shares Astropy FITS decoding, NumPy NPZ handling, source files, the mathematical specification and floating-point runtime. This is separate-agent numerical checking, not independent human or observatory validation.

The earlier200 project exposures are outside the fixed comparison scope. The audit reconstructs four event IDs numerically rather than all336. No requested sample lies outside wavelength coverage, so the no-extrapolation branch is verified by source inspection but not exercised by these data. Low-continuum records remain in aggregates and lack formal ERR uncertainties. Neither recurrence nor reference-frame preference establishes origin or a qualified SETI detection.

Run `python v2/extension02/epoch_followup/independent_audit/check_epochs.py` from any directory after restoring input spectra and profile arrays. [SUMMARY.json](SUMMARY.json) contains exact hashes, runtime versions, all100 input checks and every scalar case.
