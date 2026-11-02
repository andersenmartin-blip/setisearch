# C003 input and custody audit

PASS for the fixed HD106515A group: seven existing merged spectra, five discovery native-A products, five ancillary TARs and eight historical saved raw/native panels. All25 restored files match their hashes and original archive members. Three input ZIP archives and the reconstructed batch02 evidence archive match their historical custody records. The final inventory SHA-256 is `05548c32e4d8a20c16fe0e8549c83365b6dd74bcb38814faafde49a3717d77ca`.

The audit reads opaque bytes for hashes, FITS headers and NPY headers only. No flux or pixel values are interpreted; no network requests or historical edits occur. `INPUT_AUDIT.json` summarizes248 direct repeated metadata/identity checks by scope and lists only failures. These are reconciliation checks, not248 independent scientific tests.

All seven merged spectra have barycentric air-Angstrom wavelengths and uncalibrated ADU flux; their ERR headers declare unavailable values. The five nativeA products retain the inherited topocentric air wavelength polynomial at zero-based pixel0…4095. Native BUNIT is absent, so native flux must remain labelled instrumental/native units. Header coefficients independently reproduce the historical wavelength/trace mappings. No new orientation or wavelength fit is made.

The first discovery anchor BERV is30.1380355615464 km/s. The common barycentric midpoint3869.75125Å maps to first-anchor topocentric midpoint3869.3622643053627Å. Fixed context is±3Å at0.01Å spacing; the nominal±0.25625Å core contains51 grid centers. Each reference flank contains151 centers when covered.

| Historical native context | Barycentric support /601 | Topocentric support /601 | Core /51 | Negative / positive flank |
|---|---:|---:|---:|---:|
| 0022 order2 | 365 | 365 | 51 | 151 /0 |
| 0027 order2 | 340 | 365 | 51 | 151 /0 |
| 0044 order2 | 330 | 365 | 51 | 151 /0 |
| All five order3 contexts | 601 | 601 | 51 | 151 /151 |

These are header-derived geometric support counts, not finite-flux or normalization results. Missing order2 right-flank support remains missing. The three historical order2 contexts retain failed earlier local mapping checks and passed global/five-window checks. All five order3 contexts retain passing local/global/five-window support.

Two different exclusions must remain explicit. For0051, the original event-specific topocentric feature is3870.0700818006676Å, above order2’s3870.006051618989Å endpoint. For0053, the feature is3870.132402290935Å, above the3870.0057691951843Å endpoint. Their original order2 line contexts and raw panels therefore do not exist. The fixed first-anchor topocentric center happens to lie inside those wavelength domains; this cannot create an additional historical line-covering order. The original feature centers were independently recomputed from each event’s own barycentric center and BERV, rather than from the common context anchor.

Exact time identifiers are preserved. For0022, the raw identifier ends `07:04:47.116` while merged/native DATE-OBS ends`.115`; for0027, the raw identifier ends `04:52:12.632` while DATE-OBS ends`.631`. Both are inherited+1ms offsets. PROV1, native TAR member names and original archive mappings agree; no string normalization is applied. The report records offsets for all seven merged exposures.

`audit_inputs.py` reproduces the audit. Its only outputs are within this input_audit directory. Flux quality, gap handling, normalization and profile comparisons remain for the separately released analysis.
